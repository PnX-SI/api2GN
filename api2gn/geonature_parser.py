import click
from api2gn.parsers import JSONParser


class GeoNatureParser(JSONParser):
    # TODO : build a mapping from Synthese Model
    mapping = {}
