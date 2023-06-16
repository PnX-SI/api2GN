from sqlalchemy.sql import func

from geonature.utils.env import db
from ref_geo.utils import get_local_srid


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

    @property
    def local_srid(self):
        return get_local_srid(db.session)
