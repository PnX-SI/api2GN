import sys

import click


from api2gn.utils import list_parsers, get_parser


@click.command(name="list")
def cmd_list_parsers():
    parsers = list_parsers()
    for p in parsers:
        click.secho(f"🌵 {p.name} - {p.description}", fg="green")


@click.command()
@click.argument("name")
@click.option("--dry-run", is_flag=True)
def run(name, dry_run):
    Parser = get_parser(name)
    Parser().run(dry_run)
