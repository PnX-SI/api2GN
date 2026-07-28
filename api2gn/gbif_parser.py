import requests
import click
import time
import math
import random
from requests import Response

from pygbif import occurrences, registry
from shapely import wkt
from sqlalchemy import select
from sqlalchemy.sql import func
from geoalchemy2.shape import from_shape
from api2gn.parsers import JSONParser
from api2gn.utils import generate_date_range


from geonature.utils.env import db

from apptax.taxonomie.models import TaxrefLiens

from geonature.core.gn_meta.models import TDatasets, TAcquisitionFramework
from geonature.core.gn_synthese.models import Synthese


def calculate_gbif_precision(value):
    if "coordinateUncertaintyInMeters" in value:
        return int(value["coordinateUncertaintyInMeters"])
    # Default gps precision
    return 10


def sleep_from_retry_after(
    resp: Response, default_backoff_s: float = 1.0, attempt: int = 0
):
    """Attend selon Retry-After si présent, sinon backoff exponentiel (avec jitter)."""
    retry_after = resp.headers.get("Retry-After")
    if retry_after:
        try:
            # Retry-After peut être un nombre de secondes ou une date HTTP (RFC 7231).
            delay = float(retry_after)
        except ValueError:
            # Si c'est une date, on peut la parser; ici on applique un délai par défaut.
            delay = max(default_backoff_s, 2.0)
    else:
        # Backoff exponentiel avec jitter
        base = default_backoff_s * (2**attempt)
        delay = base + random.uniform(0, base / 2.0)
    click.secho(
        f"429 Client Error: Too Many Requests for url. Waiting up to {delay} seconds and retry",
        fg="red",
    )
    time.sleep(delay)


def get_with_rate_limit(url, params=None, max_attempts=5, session=None, timeout=30):
    sess = session or requests.Session()
    attempt = 0
    while attempt < max_attempts:
        resp = sess.get(url, params=params, timeout=timeout)
        if resp.status_code == 429:
            sleep_from_retry_after(resp, default_backoff_s=1.0, attempt=attempt)
            attempt += 1
            continue
        resp.raise_for_status()
        return resp
    raise RuntimeError(f"Échec après {max_attempts} tentatives (429 persistant).")


# https://dwc.tdwg.org/list/#dwc_occurrenceStatus
# http://rs.tdwg.org/dwc/terms/lifeStage
# http://rs.tdwg.org/dwc/terms/sex
class GBIFParser(JSONParser):
    srid = 4326
    progress_bar = False  # useless multiple single request
    row_data = {}
    create_dataset = False  # Indicate if dataset should be created
    af_id = None  # The id of the acquisition framework. If not set, it will be created with name GBIF
    datasets_id = (
        {}
    )  # A dict to store dataset id. Key is the uuid and value is the dataset id. Avoid multiple request

    # Default GBIF api filters for occurrence
    api_filters = {
        "occurrenceStatus": "PRESENT",
        "basisOfRecord": [
            "OBSERVATION",
            "HUMAN_OBSERVATION",
            "MACHINE_OBSERVATION",
            "OCCURRENCE",
        ],
        "hasGeospatialIssue": False,
        "hasCoordinate": True,
    }
    # Mapping between GBIF values and sinp nomenclature values
    cd_nomenclature_mapping = {
        "lifeStage": {
            "larva": "6",
            "juvenile": "3",
            "adult": "2",
            "seedling": "20",
            "fruiting": "27",
        },
        "sex": {
            "female": "2",
            "male": "3",
            "hermaphrodite": "4",
        },
        "occurrenceStatus": {
            "present": "Pr",
            "absent": "No",
        },
    }

    def __init__(self):
        self.api_filters = {**GBIFParser.api_filters, **self.api_filters}
        if self.limit > 300:
            # The API caps the number of items at 300 per call
            self.limit = 300
        self.mapping = {**GBIFParser.mapping, **self.mapping}
        self.constant_fields = {
            **GBIFParser.constant_fields,
            **self.constant_fields,
        }
        # Initialize the parent class
        super().__init__()
        from datetime import datetime

        # filter to have only new data
        if self.parser_obj.last_import:
            click.secho(
                f"Prepare to retrieve data new since {self.parser_obj.last_import}",
                fg="blue",
            )
            self.api_filters["lastInterpreted"] = ",".join(
                [
                    self.parser_obj.last_import.strftime("%Y-%m-%d"),
                    datetime.now().strftime("%Y-%m-%d"),
                ]
            ) 
        self.data = None

        self.validate_maping()
        if not "id_dataset" in self.constant_fields and not self.create_dataset:
            click.secho(
                f"You need to set create_dataset=True or set id_dataset in constant_fields. No data will be imported",
                fg="red",
            )
        else:
            # get or create default acquisition framework
            # if not default value is set
            if self.create_dataset and not self.af_id:
                self.af_id = self._get_or_create_af()

            self.fetch_occurrence_ids_search()

    def _test_dataset_uuid(self, uuid):
        if uuid in self.datasets_id:
            return self.datasets_id[uuid]

        dataset = db.session.execute(
            select(TDatasets).where(TDatasets.unique_dataset_id == uuid).limit(1)
        ).scalar()
        if not dataset:
            gbif_dataset = self._fetch_dataset_data()
            dataset = self._create_dataset(gbif_dataset)
        self.datasets_id[uuid] = dataset.id_dataset
        return self.datasets_id[uuid]

    def _create_dataset(self, gbif_dataset):
        """
        Create a dataset from a GBIF dataset.

        Parameters
        ----------
        gbif_dataset : dict
            A dataset from the GBIF API.

        Returns
        -------
        dataset : TDatasets
            The created dataset.
        """
        # create dataset
        dataset = TDatasets(
            unique_dataset_id=gbif_dataset["key"],
            dataset_name=gbif_dataset["title"],
            dataset_shortname=gbif_dataset["title"],
            dataset_desc=gbif_dataset["description"],
            id_acquisition_framework=self.af_id,
            marine_domain=False,
            terrestrial_domain=False,
        )
        db.session.add(dataset)
        click.secho(
            f"Create dataset {dataset.dataset_name} ...",
            fg="green",
        )
        db.session.commit()
        return dataset

    def _fetch_dataset_data(self):
        dataset_key = self.data.get("datasetKey")
        if dataset_key:
            registry.datasets(limit=1)
            return registry.datasets(uuid=dataset_key)
        return None

    def _get_or_create_af(self):
        """
        Get or create acquisition framework with name "GBIF".
        If not exist, create it and commit in database.
        Return acquisition framework id.
        """
        af = db.session.execute(
            select(TAcquisitionFramework)
            .where(TAcquisitionFramework.acquisition_framework_name == "GBIF")
            .limit(1)
        ).scalar()

        if af is None:
            af = TAcquisitionFramework(
                acquisition_framework_name="GBIF",
                acquisition_framework_desc="GBIF af",
            )
            db.session.add(af)
            click.secho(
                f"Create acquisition framework  {af.acquisition_framework_name} ...",
                fg="green",
            )
            db.session.commit()
        return af.id_acquisition_framework

    def _get_cd_nomenclature(self, field, value):
        if value:
            return self.cd_nomenclature_mapping[field].get(value.lower())
        return None

    def fetch_occurrence_ids_search(self):
        click.secho(f"Fetching data from GBIF", fg="green")
        self.gbif_search_occurence(self.limit, offset=0)

        return self.row_data

    def gbif_search_occurence(self, limit=1000, offset=0):
        self.api_filters["limit"] = self.limit
        self.api_filters["offset"] = offset

        s = requests.Session()
        try:
            response = get_with_rate_limit(
                "https://api.gbif.org/v1/occurrence/search",
                params=self.api_filters,
                session=s,
            )
            response = response.json()
        except Exception as e:
            print("Erreur:", e)

        total_number = response["count"]
        if total_number == 0:
            return
        if total_number > 100000:
            click.secho(
                "Too much data use download function first or change download params",
                fg="red",
            )
            return
        click.secho(f"Get data {offset + limit}/{total_number}", fg="green")

        search_occurence = {
            result["key"]: result
            for result in response.get("results", {})
            if "key" in result
        }
        if search_occurence:
            self.row_data = self.row_data | search_occurence
        if response["endOfRecords"] == False:
            self.gbif_search_occurence(limit=limit, offset=limit + offset)

    def fetch_taxref_cd_nom(self):
        try:
            cd_nom = db.session.scalar(
                select(TaxrefLiens.cd_nom)
                .where(TaxrefLiens.ct_name == "GBIF")
                .where(TaxrefLiens.ct_sp_id == str(self.data["taxonKey"]))
                .limit(1)
            )
            if not cd_nom:
                click.secho(
                    f'[data #{self.occurrence_id}] No matching cd_nom found for taxon: {self.data["taxonKey"]}',
                    fg="yellow",
                )
            return cd_nom
        except Exception as e:
            click.secho(
                f"[data #{self.occurrence_id}] Fetching taxref cd_nom in Error: {e}",
                fg="red",
            )

    @property
    def items(self):
        return [self.data]  # Return data as a list with a single item

    @property
    def total(self):
        return len(self.row_data)  # Nombre total d'occurrences

    def get_geom(self, row):
        if "decimalLatitude" in row and "decimalLongitude" in row:
            point = f"POINT({row['decimalLongitude']} {row['decimalLatitude']})"
            geom = wkt.loads(point)
            return from_shape(geom, srid=4326)
        else:
            click.secho(
                f"[data #{self.occurrence_id}] Could not get geom X/Y fields",
                fg="yellow",
            )
        return None

    def build_object(self, row):
        if not row:
            return None

        existing_synthese = row.pop("_existing_synthese", None)
        parsed_synthese = super().build_object(row)

        if parsed_synthese is None or existing_synthese is None:
            return parsed_synthese

        for attribute, value in vars(parsed_synthese).items():
            if attribute in {"_sa_instance_state", "id_synthese"}:
                continue
            setattr(existing_synthese, attribute, value)

        return existing_synthese

    def next_row(self):
        for occurrence_id, data in self.row_data.items():
            self.counter += 1
            self.occurrence_id = occurrence_id
            self.data = data
            try:
                from uuid import UUID

                identifier = self.data["identifiers"][0]["identifier"]
                self.data["identifier"] = UUID(identifier)
            except (ValueError, KeyError):
                self.data["identifier"] = None
            self.data["cd_nom"] = self.fetch_taxref_cd_nom()
            nomeclature_key = ["sex", "lifeStage", "occurrenceStatus"]
            for key in nomeclature_key:
                self.data[key] = self._get_cd_nomenclature(key, self.data.get(key))

            if self.data["cd_nom"]:
                # Populate self.data["id_dataset"]
                if self.data.get("id_dataset") is None:
                    if self.create_dataset:
                        dataset_key = self.data.get("datasetKey")
                        if dataset_key is None:
                            raise ValueError(
                                "datasetKey is required when create_dataset=True"
                            )
                        id_dataset = self._test_dataset_uuid(dataset_key)
                    else:
                        id_dataset = self.constant_fields.get("id_dataset")
                        if id_dataset is None:
                            raise ValueError(
                                "id_dataset must be provided in constant_fields "
                                "when create_dataset=False"
                            )

                    self.data["id_dataset"] = id_dataset

                # Check if data is already in db
                # if true updata row
                synthese_data = db.session.scalar(
                    select(Synthese)
                    .where(Synthese.entity_source_pk_value == self.data["gbifID"])
                    .where(Synthese.id_dataset == self.data["id_dataset"])
                    .limit(1)
                )
                if synthese_data:
                    click.secho(
                        f"[data #{self.occurrence_id}] Update existing synthese row {synthese_data.id_synthese}",
                        fg="blue",
                    )
                    self.data["_existing_synthese"] = synthese_data

                if "eventDate" in self.data:
                    try:
                        date_min, date_max = generate_date_range(self.data["eventDate"])
                        self.data.update({"dateStart": date_min, "dateEnd": date_max})

                    except ValueError as e:
                        click.secho(
                            f"[data #{self.occurrence_id}] Could not get properly occurence date: {e}",
                            fg="red",
                        )
                    yield None
                yield self.data
            else:
                yield None

    dynamic_fields = {"precision": calculate_gbif_precision}
    ### Mapping a améliorer
    mapping = {
        "unique_id_sinp": "identifier",
        "date_min": "dateStart",
        "date_max": "dateEnd",
        "nom_cite": "scientificName",
        "count_min": "individualCount",
        "count_max": "individualCount",
        "observers": "recordedBy",
        "determiner": "recordedBy",
        "place_name": "verbatimLocality",
        "entity_source_pk_value": "gbifID",
        "cd_nom": "cd_nom",
        "id_nomenclature_sex": "sex",
        "id_nomenclature_life_stage": "lifeStage",
        "id_nomenclature_observation_status": "occurrenceStatus",
        "id_dataset": "id_dataset",
    }
