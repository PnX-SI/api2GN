import sys

import click


from api2gn.utils import list_parsers, get_parser


def print_parsers(parsers):
    for parser in parsers:
        click.secho(f"🌵 {parser.name} - {parser.description}", fg="green")


@click.command(name="list")
def cmd_list_parsers():
    print_parsers(list_parsers())


@click.command()
@click.argument("name")
@click.option("--dry-run", is_flag=True)
def run(name, dry_run):
    Parser = get_parser(name)
    if Parser is None:
        parsers = list_parsers()
        click.secho("Available parsers:", fg="yellow")
        print_parsers(parsers)
        raise click.ClickException(f"Cannot find parser '{name}'")

    Parser().run(dry_run)
