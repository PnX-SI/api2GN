import requests
import xml.etree.ElementTree as ET
import pygml
from time import sleep

from datetime import datetime
import click

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
    name: str
    mapping = dict()
    constant_fields = dict()
    dynamic_fields = dict()
    limit: int = 100
    url: str
    api_filters = dict()
    srid = None
    page_parameter = "page"

    def __init__(
        self,
    ):
        MappingValidator({**self.mapping, **self.constant_fields}).validate()
        self.geometry_col = (
            "the_geom_local" if self.local_srid == self.srid else "the_geom_4326"
        )
        self.parser_obj = self._get_or_create_parser()
        self.last_import = ParserModel.query.filter_by(name=self.name).one().last_import

    @property
    def items(self):
        return self.root

    def _get_or_create_parser(self):
        parser = ParserModel.query.filter_by(name=self.name).one_or_none()
        if not parser:
            parser = ParserModel(name=self.name, type=self.__class__.__name__)
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

    def next_row(self):
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
        db.session.commit()

    def run(self):
        click.secho(f"Start import {self.name} ...", fg="green")
        self.start()
        nb_rows = 0
        for row in self.next_row():
            obj = self.build_object(row)
            self.insert(obj)
            nb_rows += 1

        db.session.commit()
        self.save_history()
        self.end()
        click.secho(f"Successfully import {nb_rows} row(s)", fg="green")


class JSONParser(Parser):
    def __init__(self):
        super().__init__()

    def get_geom(self, row):
        """
        Must return a wkb geom
        """
        shapely_geom = shape(row["geometry"])
        return from_shape(shapely_geom)

    def build_object(self, row):
        synthese_dict = {}
        for gn_col, const in self.constant_fields.items():
            synthese_dict[gn_col] = const
            self.mapping.pop(gn_col, None)
        for gn_col, func in self.dynamic_fields.items():
            row_value = self.mapping.pop(gn_col)
            synthese_dict[gn_col] = func(row_value)

        for gn_col, json_key in self.mapping.items():
            if gn_col.startswith("id_nomenclature"):
                synthese_dict[gn_col] = func.ref_nomenclatures.get_id_nomenclature(
                    self.nomenclature_mapping[gn_col], row[json_key["key"]]
                )
            else:
                synthese_dict[gn_col] = row[json_key]
        wkb_geom = self.get_geom(row)
        if wkb_geom:
            synthese_dict = self.fill_dict_with_geom(synthese_dict, wkb_geom)
        return Synthese(**synthese_dict)

    def next_row(self):
        while True:
            filters = {
                **self.api_filters,
                self.page_parameter: 0,
                self.limit: self.limit,
            }
            response = self.request_or_retry(self.url, params=filters)
            self.root = response.json()
            for row in self.items:
                yield row
            if len(self.items) < self.limit:
                break
            self.api_filters[self.page_parameter] += 1


class WFSParser(Parser):
    layer: str
    wfs_version: str

    def __init__(self):
        super().__init__()

    @property
    def items(self):
        return self.root.text

    def get_xml_value(self, parent_tag, xml_key):
        default = None
        if ":" in xml_key:
            xml_key, default = xml_key.split(":")
        new_tag = parent_tag.find(".//{*}" + xml_key)
        if new_tag is None:
            return default or xml_key
        else:
            return new_tag.text or default

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
                return geom.geometry
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
            count_or_max_feature: self.limit,
            "service": "WFS",
        }
        self.root = self.request_or_retry(self.url, params=api_filters)
        xml_root = ET.fromstring(self.items)
        for xml_node in xml_root:
            yield xml_node

    def late_filter_feature(self, feature):
        """
        In WFS filters are hard to implement, but with this fonction you can
        implement "late filters". The API will fetch all data, but only the features
        match the filter will be return by the build_objects func
        """
        return True

    def build_object(self, row):
        current_tag = row[0]
        synthese_dict_value = {}
        if not self.late_filter_feature(current_tag):
            return
        for gn_col, xml_key in self.mapping.items():
            val = self.get_xml_value(current_tag, xml_key)
            synthese_dict_value[gn_col] = val
        # geom
        geom = self.get_geom(current_tag)
        if geom:
            shapely_geom = shape(geom)
            wkb_geom = from_shape(shapely_geom)
            synthese_dict_value[self.geometry_col] = wkb_geom
            if self.geometry_col == "the_geom_local":
                synthese_dict_value["the_geom_4326"] = self.build_geom_4326(
                    wkb_geom, 2154
                )
                synthese_dict_value[
                    "the_geom_point"
                ] = self.build_centroid_4326_from_local(wkb_geom, 2154)
            elif self.geometry_col == "the_geom_4326":
                synthese_dict_value["the_geom_local"] = self.build_geom_local(
                    wkb_geom, 2154
                )
                synthese_dict_value["the_geom_point"] = self.build_centroid_from_4326(
                    wkb_geom
                )
            return Synthese(**synthese_dict_value)
