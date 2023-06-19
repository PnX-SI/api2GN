from api2gn.parsers import WFSParser
from api2gn.geonature_parser import GeoNatureParser


class GeoNatureParserOne(GeoNatureParser):
    name = "GN Flavia"
    url = "http://geonature.fr/truc"
    mapping = {
        "date_max": "lala",
        "date_min": "lala",
        "id_source": "lala",
        "nom_cite": "lala",
    }
    srid = 2154


class OtherParser(WFSParser):
    name = "GN LPO"
    url = "http://geonature.fr/truc"
    mapping = {}
    srid = 2154
