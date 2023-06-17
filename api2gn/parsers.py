import requests
import xml.etree.ElementTree as ET
import pygml
import sleep

from datetime import datetime
import click

from shapely.geometry import shape
from geoalchemy2.shape import from_shape


from geonature.core.gn_synthese.models import Synthese
from geonature.utils.env import db
from geonature.utils.config import config

from api2gn.schema import MappingValidator
from api2gn.mixins import GeometryMixin
from api2gn.models import ParserModel


module_config = config["API2GN"]


class Parser(GeometryMixin):
    name: str
    mapping = dict()
    limit: int = 100
    url: str
    api_filters = dict()
    srid = None
    page_parameter = "page"

    def __init__(
        self,
    ):
        MappingValidator(self.mapping).validate(self.mapping)
        self.geometry_col = (
            "the_geom_local" if self.local_srid == self.srid else "the_geom_4326"
        )
        self.parser_obj = self._get_or_create_parser()
        self.last_import = ParserModel.query.filter_by(name=self.name).one().last_import

    def _get_or_create_parser(self):
        parser = ParserModel.query.filter_by(name=self.name).one_or_none()
        if not parser:
            parser = ParserModel(name=self.name, type=self.__class__.__name__)
            db.session.add(parser)
            db.session.commit()

    def request_or_retry(self, url, **kwargs):
        try_get = module_config.PARSER_NUMBER_OF_TRIES
        assert try_get > 0
        while try_get:
            response = requests.get(url, allow_redirects=True, **kwargs)
            if response.status_code in module_config.PARSER_RETRY_HTTP_STATUS:
                click.info("Failed to fetch url {}. Retrying ...".format(url))
                sleep(module_config.PARSER_RETRY_SLEEP_TIME)
                try_get -= 1
            elif response.status_code == 200:
                return response
            else:
                break
        click.warning(
            "Failed to fetch {} after {} times. Status code : {}.".format(
                url, module_config.PARSER_NUMBER_OF_TRIES, response.status_code
            )
        )
        raise click.ClickException(
            _("Failed to download {url}. HTTP status code {status_code}").format(
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
        self.save_history(nb_rows)
        self.end()
        click.secho(f"Successfully import {nb_rows} row(s)", fg="green")


class JSONParser(Parser):
    def __init__(self):
        super().__init__()

    def build_object(self):
        # TODO
        pass

    def next_row(self):
        while True:
            filters = {
                **self.api_filters,
                self.page_parameter: 0,
                self.limit: self.limit,
            }
            response = self.request_or_retry(self.url, params=filters)
            data = response.json()
            for row in data:
                yield row
            if len(data) < self.limit:
                break
            self.api_filters[self.page_parameter] += 1


class WFSParser(Parser):
    layer: str
    wfs_version: str

    def __init__(self):
        super().__init__()

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
        response = self.request_or_retry(self.url, params=api_filters)
        xml_root = ET.fromstring(response.text)
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
