import sys

import click


from api2gn.utils import list_parsers, get_parser


@click.command(name="list")
def cmd_list_parsers():
    parsers = list_parsers()
    for p in parsers:
        click.secho(f"🌵 {p}", fg="green")


@click.command()
@click.argument("name")
def run(name):
    Parser = get_parser(name)
    Parser().run()


class Foo:
    f = {"la": "lo"}


class Bar(Foo):
    f = {"bis": "ho"}

    def __init__(self) -> None:
        super().__init__()
        self.f = {**Bar.f, **self.f}


class Ter(Bar):
    f = {"encoreautretruc": "lala"}


@click.command()
def test():
    t = Ter()
    print(t.f)
