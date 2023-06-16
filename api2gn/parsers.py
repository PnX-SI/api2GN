import requests
import xml.etree.ElementTree as ET
import pygml

from datetime import datetime
import click

from shapely.geometry import shape
from geoalchemy2.shape import from_shape


from geonature.core.gn_synthese.models import Synthese
from geonature.utils.env import db

from api2gn.schema import MappingValidator
from api2gn.mixins import GeometryMixin
from api2gn.models import ParserModel


class Parser(GeometryMixin):
    name: str
    mapping = dict()
    limit: int = 100
    url: str
    api_filters = dict()
    srid = None

    def __init__(self, srid=None, mapping={}, name=None):
        self.mapping = {**mapping, **self.mapping}
        MappingValidator(self.mapping).validate(self.mapping)
        self.srid = srid or self.srid
        self.name = name or self.name
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

    def fetch_data(self, filters={}):
        raise NotImplemented

    def build_objects(self):
        raise NotImplemented

    def insert(self, obj):
        db.session.add(obj)

    def save_history(self, nb_row):
        self.parser_obj.last_import = datetime.now()
        db.session.commit()

    def run(self):
        click.secho(f"Start import {self.name} ...", fg="green")
        filters = {"page": 0}
        nb_line = 0
        while True:
            data = self.fetch_data(filters)
            for obj in self.build_objects(data):
                self.insert(obj)
            nb_line = nb_line + len(data)
            if not data or (data and len(data) < self.limit):
                db.session.commit()
                self.save_history(nb_line)
                click.secho(f"Successfully import {nb_line} row(s)", fg="green")

                break
            filters["page"] = filters["page"] + 1


class JSONParser(Parser):
    def __init__(self, srid=None, mapping={}, name=None):
        super().__init__(srid, mapping, name)

    def build_object(self):
        pass


class WFSParser(Parser):
    layer: str
    wfs_version: str

    def __init__(self, srid=None, mapping={}, name=None):
        super().__init__(srid, mapping)

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

    def fetch_data(self, filters={}):
        # wfs = WebFeatureService(url=self.url, version=self.wfs["wfs_version"])

        # _filter = PropertyIsEqualTo("code_dept", "05")
        # filterxml = etree.tostring(_filter.toXML()).decode("utf-8")
        # # response = wfs11.getfeature(typename='bvv:gmd_ex')
        # response = wfs.getfeature(
        #     typename=self.wfs["layer"],
        #     propertyname=["o06_date", "code_dept"],
        #     filter=filterxml,
        # )
        # out = open("/tmp/data.gml", "wb")
        # out.write(response.read())
        # out.close()
        # return None
        # return wfs.getfeature(typename=self.wfs["layer"])
        count_or_max_feature = (
            "count" if self.wfs_version in ("2.0.0", "2.0.1") else "maxFeatures"
        )
        api_filters = {
            **self.api_filters,
            **filters,
            "version": self.wfs_version,
            "request": "GetFeature",
            "TYPENAME": self.layer,
            count_or_max_feature: self.limit,
            "service": "WFS",
        }
        response = requests.get(self.url, params=api_filters)
        if response.status_code == 200:
            return ET.fromstring(response.text)
        else:
            raise requests.exceptions.HTTPError("Fail to fetch the WFS")

    def late_filter_feature(self, feature):
        """
        In WFS filters are hard to implement, but with this fonction you can
        implement "late filters". The API will fetch all data, but only the features
        match the filter will be return by the build_objects func
        """
        return True

    def build_objects(self, data):
        for node in data:
            current_tag = node[0]
            synthese_dict_value = {}
            if not self.late_filter_feature(current_tag):
                continue
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
                    synthese_dict_value[
                        "the_geom_point"
                    ] = self.build_centroid_from_4326(wkb_geom)
            yield Synthese(**synthese_dict_value)
