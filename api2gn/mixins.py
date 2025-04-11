from sqlalchemy.sql import func

from geonature.utils.env import db
from ref_geo.utils import get_local_srid

from shapely.geometry import shape
from geoalchemy2.shape import from_shape


class NomenclatureMixin:
    nomenclature_mapping = {
        "id_nomenclature_info_geo_type": "TYP_INF_GEO",
        "id_nomenclature_grp_typ": "TYP_INF_GEO",
        "id_nomenclature_behaviour": "OCC_COMPORTEMENT",
        "id_nomenclature_obs_technique": "METH_OBS",
        "id_nomenclature_bio_status": "STATUT_BIO",
        "id_nomenclature_bio_condition": "ETA_BIO",
        "id_nomenclature_naturalness": "NATURALITE",
        "id_nomenclature_exist_proof": "PREUVE_EXIST",
        "id_nomenclature_obj_count": "OBJ_DENBR",
        "id_nomenclature_sensitivity": "SENSIBILITE",
        "id_nomenclature_observation_status": "STATUT_OBS",
        "id_nomenclature_blurring": "DEE_FLOU",
        "id_nomenclature_source_status": "STATUT_SOURCE",
        "id_nomenclature_determination_method": "METH_DETERMIN",
        "id_nomenclature_sex": "SEXE",
        "id_nomenclature_life_stage": "STADE_VIE",
    }


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

    def fill_dict_with_geom(self, synthese_dict, wkb_geom):
        synthese_dict[self.geometry_col] = wkb_geom
        if self.geometry_col == "the_geom_local":
            synthese_dict["the_geom_4326"] = self.build_geom_4326(wkb_geom, 2154)
            synthese_dict["the_geom_point"] = self.build_centroid_4326_from_local(
                wkb_geom, 2154
            )
        elif self.geometry_col == "the_geom_4326":
            synthese_dict["the_geom_local"] = self.build_geom_local(wkb_geom, 2154)
            synthese_dict["the_geom_point"] = self.build_centroid_from_4326(wkb_geom)
        return synthese_dict

    @property
    def local_srid(self):
        return get_local_srid(db.session)
