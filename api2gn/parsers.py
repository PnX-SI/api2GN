import requests
import xml.etree.ElementTree as ET
import pygml
from time import sleep


from datetime import datetime
import click

from tqdm import tqdm
from sqlalchemy.sql import func
from shapely.geometry import shape
from geoalchemy2.shape import from_shape

from geonature.core.gn_synthese.models import Synthese
from geonature.utils.env import db
from geonature.utils.config import config

from api2gn.schema import MappingValidator
from api2gn.mixins import GeometryMixin, NomenclatureMixin
from api2gn.models import ParserModel


module_config = config["API2GN"]


class Parser(GeometryMixin, NomenclatureMixin):
    """
    Attributes:
        mapping(dict): TODO
        constant_fields(dict): TODO
        dynamic_fields(dict): TODO
    """

    name: str
    description: str = ""
    mapping = dict()
    constant_fields = dict()
    dynamic_fields = dict()
    additionnal_fields = dict()
    limit: int = None
    url: str
    api_filters = dict()
    srid = None
    progress_bar = False
    page_parameter = "page"
    limit_parameter = "limit"

    def __init__(
        self,
    ):
        self.geometry_col = (
            "the_geom_local" if self.local_srid == self.srid else "the_geom_4326"
        )
        self.parser_obj = self._get_or_create_parser()
        self.validate_maping()

    def validate_maping(self):
        """
        Validate the mapping throw the model (only Synthese model implemented)
        """
        MappingValidator(
            {**self.mapping, **self.constant_fields, **self.dynamic_fields}
        ).validate()

    @property
    def items(self):
        return self.root

    def _get_or_create_parser(self):
        parser = ParserModel.query.filter_by(name=self.name).one_or_none()
        if not parser:
            parser = ParserModel(
                name=self.name,
                description=self.description,
            )
            db.session.add(parser)
            db.session.commit()
        return parser

    def request_or_retry(self, url, **kwargs):
        try_get = module_config["PARSER_NUMBER_OF_TRIES"]
        assert try_get > 0
        while try_get:
            response = requests.get(url, allow_redirects=True, **kwargs)
            if response.status_code in module_config["PARSER_RETRY_HTTP_STATUS"]:
                click.info("Failed to fetch url {}. Retrying ...".format(url))
                sleep(module_config["PARSER_RETRY_SLEEP_TIME"])
                try_get -= 1
            elif response.status_code == 200:
                return response
            else:
                break
        click.secho(
            "Failed to fetch {} after {} times. Status code : {}.".format(
                url, module_config["PARSER_NUMBER_OF_TRIES"], response.status_code
            ),
            fg="red",
        )
        raise click.ClickException(
            ("Failed to download {url}. HTTP status code {status_code}").format(
                url=response.url, status_code=response.status_code
            )
        )

    def next_row(self, page=0):
        raise NotImplemented

    def build_object(self):
        raise NotImplemented

    def insert(self, obj):
        db.session.add(obj)

    def start(self):
        pass

    def end(self):
        pass

    def save_history(self):
        self.parser_obj.last_import = datetime.now()
        self.parser_obj.nb_row_last_import = self.nb_row_imported
        self.parser_obj.nb_row_total = self.nb_row_imported + (
            self.parser_obj.nb_row_total or 0
        )
        db.session.commit()

    def run(self, dry_run=False):
        click.secho(f"Start import {self.name} ...", fg="green")
        self.start()
        self.nb_row_imported = 0
        previous_percetage = 0
        click.secho("Fetching data from source", fg="green")
        if self.progress_bar:
            pbar = tqdm(total=100)
        for row in self.next_row():
            obj = self.build_object(row)
            if not obj:
                continue
            self.insert(obj)
            self.nb_row_imported += 1
            if self.progress_bar:
                previous_percetage = (self.nb_row_imported / self.total) * 100
                new_percentage = (self.nb_row_imported / self.total) * 100
                to_update = new_percentage - previous_percetage
                pbar.update(to_update)
        if self.progress_bar:
            pbar.close()

        click.secho(
            "Successfully fetch data from source. Inserting data in db now...",
            fg="green",
        )
        if not dry_run:
            db.session.commit()
        self.save_history()
        self.end()
        click.secho(f"Successfully import {self.nb_row_imported} row(s)", fg="green")


class JSONParser(Parser):
    limit = 100

    def validate_maping(self):
        """
        Validate the mapping throw the model (only Synthese model implemented)
        """
        MappingValidator(
            {**self.mapping, **self.constant_fields, **self.dynamic_fields}
        ).validate()
        
    def get_geom(self, row):
        """
        Must return a wkb geom
        """
        shapely_geom = shape(row["geometry"])
        return from_shape(shapely_geom, srid=self.srid)

    def build_object(self, row):
        synthese_dict = {}
        for gn_col, const in self.constant_fields.items():
            synthese_dict[gn_col] = const
            self.mapping.pop(gn_col, None)
        for gn_col, _func in self.dynamic_fields.items():
            synthese_dict[gn_col] = _func(row)
            self.mapping.pop(gn_col, None)
        if self.additionnal_fields:
            for add_field, json_field in self.additionnal_fields.items():
                self.mapping.pop(add_field, None)
                synthese_dict.setdefault("additional_data", {})[add_field] = row[
                    json_field
                ]

        for gn_col, json_field in self.mapping.items():
            if gn_col.startswith("id_nomenclature"):
                try:
                    nomenclature_mnemonique_type = self.nomenclature_mapping[gn_col]
                except KeyError as e:
                    click.secho(
                        f"\nCannot find a nomenclature mnemonique type for `{gn_col}` - Please update the `nomenclature_mapping` class attribute",
                        fg="red",
                    )
                    raise click.ClickException("Stop import")
                synthese_dict[gn_col] = func.ref_nomenclatures.get_id_nomenclature(
                    nomenclature_mnemonique_type, row[json_field]
                )
            else:
                synthese_dict[gn_col] = row[json_field]
        wkb_geom = self.get_geom(row)
        if wkb_geom:
            synthese_dict = self.fill_dict_with_geom(synthese_dict, wkb_geom)
        return Synthese(**synthese_dict)

    def next_row(self, page=0):
        filters = {
            **self.api_filters,
            self.page_parameter: page,
            self.limit_parameter: self.limit,
        }
        while True:
            response = self.request_or_retry(self.url, params=filters)
            self.root = response.json()
            for row in self.items:
                yield row
            if len(self.items) < self.limit:
                break
            filters[self.page_parameter] += 1


class WFSParser(Parser):
    layer: str
    wfs_version: str

    @property
    def sub_items(self):
        """
        In XML items can be nested.
        In the build_object func, self.row_root = row
        From self.row_root define how access to items
        """
        return self.row_root

    @property
    def items(self):
        return ET.fromstring(self.root.text)

    def get_xml_value(self, parent_tag, xml_key):
        new_tag = parent_tag.find(".//{*}" + xml_key)
        if new_tag is None:
            return None
        else:
            return new_tag.text

    def get_geom(self, xml_feature):
        # the tag containing the gml
        geometry_parent_tag = xml_feature.find(
            ".//{*}" + self.mapping[self.geometry_col]
        )
        if geometry_parent_tag:
            geometry_tag = None
            for geometry_type in ("Point", "LineString", "Polygon"):
                geometry_tag = geometry_parent_tag.find(".//{*}" + geometry_type)
                if geometry_tag:
                    break
            if geometry_tag is not None:
                geom = pygml.parse(
                    ET.tostring(geometry_tag, encoding="unicode", method="xml")
                )
                shapely_geom = shape(geom.geometry)
                return from_shape(shapely_geom, srid=self.srid)
            else:
                print("Geometry tag not found for this feature")
                return None
        print(f"Tag containning geometry ({self.mapping[self.geometry_col]}) not found")
        return None

    def next_row(self):
        """
        The WFS parser do not implement pagination as WFS is a mess !!
        It fetch all the stream at once. Maybe won't work for big data quantity
        """

        count_or_max_feature = (
            "count" if self.wfs_version in ("2.0.0", "2.0.1") else "maxFeatures"
        )
        api_filters = {
            "version": self.wfs_version,
            "request": "GetFeature",
            "TYPENAME": self.layer,
            "service": "WFS",
        }
        if self.limit:
            api_filters[count_or_max_feature] = self.limit
        self.root = self.request_or_retry(self.url, params=api_filters)
        for xml_node in self.items:
            yield xml_node

    def late_filter_feature(self, feature):
        """
        In WFS filters are hard to implement, but with this fonction you can
        implement "late filters". The API will fetch all data, but only the features
        match the filter will be return by the build_objects func
        """
        return True

    def build_object(self, row):
        self.row_root = row
        synthese_dict_value = {}
        if not self.late_filter_feature(self.sub_items):
            return
        for gn_col, const_value in self.constant_fields.items():
            self.mapping.pop(gn_col, None)
            synthese_dict_value[gn_col] = const_value
        for gn_col, _func in self.dynamic_fields.items():
            self.mapping.pop(gn_col, None)
            synthese_dict_value[gn_col] = _func(self.sub_items)
        if self.additionnal_fields:
            for add_field, xml_key in self.additionnal_fields.items():
                self.mapping.pop(add_field, None)
                synthese_dict_value.setdefault("additional_data", {})[
                    add_field
                ] = self.get_xml_value(self.sub_items, xml_key)
        for gn_col, xml_key in self.mapping.items():
            val = self.get_xml_value(self.sub_items, xml_key)
            synthese_dict_value[gn_col] = val
        # geom
        wkb_geom = self.get_geom(self.sub_items)
        if wkb_geom:
            synthese_dict_value = self.fill_dict_with_geom(
                synthese_dict_value, wkb_geom
            )

        return Synthese(**synthese_dict_value)
