import sys

import click


from api2gn.utils import list_parsers, get_parser


@click.command(name="list")
def cmd_list_parsers():
    parsers = list_parsers()
    for p in parsers:
        click.secho(f"🌵 {p.name}", fg="green")


@click.command()
@click.argument("name")
def run(name):
    Parser = get_parser(name)
    Parser().run()
