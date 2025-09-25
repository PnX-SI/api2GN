from pygbif import occurrences, registry
from shapely import wkt
from sqlalchemy import select
from sqlalchemy.sql import func
from geoalchemy2.shape import from_shape
from api2gn.parsers import JSONParser
from api2gn.utils import generate_date_range
import requests
import click

from geonature.utils.env import db

from apptax.taxonomie.models import TaxrefLiens


# https://dwc.tdwg.org/list/#dwc_occurrenceStatus
# http://rs.tdwg.org/dwc/terms/lifeStage
# http://rs.tdwg.org/dwc/terms/sex
class GBIFParser(JSONParser):
    srid = 4326
    progress_bar = False  # useless multiple single request
    row_data = {}
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
        self.occurrence_id = None  # Initialisation
        self.data = None
        self.organization_data = None
        self.dataset_data = None
        self.species_data = None
        self.subdivisions_data = None

        self.validate_maping()

        self.fetch_occurrence_ids_search()

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
        response = occurrences.search(**dict(self.api_filters))

        total_number = response["count"]
        if total_number == 0:
            return
        if total_number > 100000:
            click.secho(
                "To much data use download function first or change download params",
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

    def fetch_occurrence_data(self, occurrence_id):
        return self.row_data[occurrence_id]

    def fetch_organization_data(self):
        organization_key = self.data.get("publishingOrgKey")
        if organization_key:
            return registry.organizations(uuid=organization_key)
        return {}

    def fetch_dataset_data(self):
        dataset_key = self.data.get("datasetKey")
        if dataset_key:
            return registry.datasets(uuid=dataset_key)
        return {}

    def fetch_subdivisions_data(self):
        url = "https://api.gbif.org/v1/geocode/gadm/FRA.3_1/subdivisions"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

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

            # self.organization_data = self.fetch_organization_data()
            # self.dataset_data = self.fetch_dataset_data()
            # self.subdivisions_data = self.fetch_subdivisions_data()

            if self.data["cd_nom"]:
                if "eventDate" in self.data:
                    try:
                        date_min, date_max = generate_date_range(self.data["eventDate"])
                        self.data.update({"dateStart": date_min, "dateEnd": date_max})
                        yield self.data
                    except ValueError as e:
                        click.secho(
                            f"[data #{self.occurrence_id}] Could not get properly occurence date: {e}",
                            fg="red",
                        )
            else:
                yield None

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
        "entity_source_pk_value": "catalogNumber",
        "cd_nom": "cd_nom",
        "id_nomenclature_sex": "sex",
        "id_nomenclature_life_stage": "lifeStage",
        "id_nomenclature_observation_status": "occurrenceStatus",
    }
