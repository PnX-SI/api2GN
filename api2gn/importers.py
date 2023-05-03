import requests
import sys
import xml.etree.ElementTree as ET
import pygml

from click.exceptions import ClickException
from shapely.geometry import shape
from geoalchemy2.shape import from_shape
from sqlalchemy.sql import func

from owslib.fes import PropertyIsLike, PropertyIsEqualTo
from owslib.etree import etree
from owslib.wfs import WebFeatureService

from geonature.core.gn_synthese.models import Synthese
from geonature.utils.env import db


class GeometryMixin:
    def build_geom_local(self, geom_4326, srid):
        return func.st_transform(func.st_setsrid(geom_4326, 4326), srid)

    def build_geom_4326(self, geom, origin_srid):
        return func.st_transform(func.st_setsrid(geom, origin_srid), 4326)

    def build_centroid_4326_from_local(self, geom, origin_srid):
        return func.st_centroid(
            func.st_transform(func.st_setsrid(geom, origin_srid), 4326)
        )

    def build_centroid_from_4326(self, geom):
        return func.st_centroid(geom)

    def geom_from_geojson(geojson):
        return func.st_geomfromgeojson()


class Importer(GeometryMixin):
    model = None

    def __init__(self, schema):
        self.url = schema["url"]
        self.geometry_col = schema["geometry_col"]
        self.mapping = schema["mapping"]
        self.limit = schema["limit"]

    def fetch_data(self):
        raise NotImplemented

    def build_objects(self):
        raise NotImplemented

    def insert(self, obj):
        db.session.add(obj)


class JSONImporter(Importer):
    def build_object(self):
        pass


class WFSImporter(Importer):
    def __init__(self, schema):
        super().__init__(schema)
        self.layer = schema["wfs"]["layer"]
        self.version = schema["wfs"]["version"]

    def get_xml_value(self, parent_tag, xml_key):
        default = None
        if ":" in xml_key:
            xml_key, default = xml_key.split(":")
        new_tag = parent_tag.find(".//{*}" + xml_key)
        if new_tag is None:
            return xml_key
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

    def fetch_data(self):
        # wfs = WebFeatureService(url=self.url, version=self.wfs["version"])

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
            "count" if self.version in ("2.0.0", "2.0.1") else "maxFeatures"
        )
        response = requests.get(
            self.url,
            params={
                "version": self.version,
                "request": "GetFeature",
                "TYPENAME": self.layer,
                count_or_max_feature: self.limit,
                "service": "WFS",
            },
        )
        if response.status_code == 200:
            return ET.fromstring(response.text)
        else:
            raise requests.exceptions.HTTPError("Fail to fetch the WFS")

    def build_objects(self, data):
        for node in data:
            current_tag = node[0]
            synthese_dict_value = {}
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
                    print("FINALLY", synthese_dict_value)
                elif self.geometry_col == "the_geom_4326":
                    synthese_dict_value["the_geom_local"] = self.build_geom_local(
                        wkb_geom, 2154
                    )
                    synthese_dict_value[
                        "the_geom_point"
                    ] = self.build_centroid_from_4326(wkb_geom)
            yield Synthese(**synthese_dict_value)
