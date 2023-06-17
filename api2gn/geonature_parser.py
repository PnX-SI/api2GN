import click
from api2gn.parsers import JSONParser


class GeoNatureParser(JSONParser):
    def __init__(self):
        super().__init__()
        self.api_filters = {**GeoNatureParser.api_filters, **self.api_filters}
        self.mapping = {**GeoNatureParser.mapping, **self.mapping}

    # TODO : build a mapping from Synthese Model
    mapping = {}
