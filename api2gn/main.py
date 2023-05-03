import sys
import click
from geonature import create_app
from geonature.utils.env import db
from geonature.core.command import main

from api2gn.config import config
from api2gn.schema import ImportSchema
from api2gn.importers import JSONImporter, WFSImporter

importer_mapping = {"wfs": WFSImporter, "json": JSONImporter}


@click.group()
def cli():
    pass


@click.command()
def run():
    gn_app = create_app()
    with gn_app.app_context():
        for imp in config["IMPORTS_NAME"]:
            try:
                import_config = config[imp]
            except KeyError:
                print(f"Missing config for {imp}")

            import_schema = ImportSchema().load(import_config)
            importer = importer_mapping.get(import_schema["type"])(import_schema)
            data = importer.fetch_data()

        for db_obj in importer.build_objects(data):
            importer.insert(db_obj)
        db.session.commit()


cli.add_command(run)


# from owslib.fes import *
# from owslib.etree import etree
# from owslib.wfs import WebFeatureService

# ogm_wfs = WebFeatureService(
#     url="https://geo.ofb.fr/adws/service/wfs/5785f7ea-a1fc-11eb-ab81-cf3094e6aea9",
#     version="1.1.0",
# )

# filter = PropertyIsLike(propertyname="bez_gem", literal="Ingolstadt", wildCard="*")
# filterxml = etree.tostring(filter.toXML()).decode("utf-8")
# response = wfs11.getfeature(typename="bvv:gmd_ex")
