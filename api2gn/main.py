import sys

import click


from geonature import create_app
from geonature.utils.env import db
from geonature.core.command import main

from api2gn.utils import list_parsers, get_parser
from api2gn.geonature_parser import external_gn


@click.group()
def cli():
    # push app context in all sub commands
    create_app().app_context().push()


cli.add_command(external_gn)


@cli.command(name="list")
def list_parsers():
    parsers = list_parsers()
    for p in parsers:
        click.secho(f"🌵 {p}", fg="green")


@cli.command()
@click.argument(
    "name",
)
def run(name):
    Parser = get_parser(name)
    Parser().run()
