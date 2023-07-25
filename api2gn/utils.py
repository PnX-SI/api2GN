import inspect
from importlib import import_module
import click


def list_parsers():
    module = import_module("api2gn.var.config.parsers")
    parsers = []
    for name, obj in inspect.getmembers(module):
        if hasattr(obj, "__module__"):
            if obj.__module__ == "api2gn.var.config.parsers" and inspect.isclass(obj):
                parsers.append(obj)
    return parsers


def get_parser(name):
    selected_parser = None
    for parser in list_parsers():
        if parser.name == name:
            selected_parser = parser
    if not selected_parser:
        click.secho(f"Cannot find parser {name}")
    module = import_module("api2gn.var.config.parsers")
    return getattr(module, selected_parser.__name__)
