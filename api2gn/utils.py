import inspect
from importlib import import_module


def list_parsers():
    module = import_module("api2gn.var.config.parsers")
    parsers = []
    for name, obj in inspect.getmembers(module):
        if hasattr(obj, "__module__"):
            if obj.__module__ == "api2gn.var.config.parsers":
                parsers.append(name)
    return parsers


def get_parser(name):
    parsers = list_parsers()
    index = parsers.index(name)
    module = import_module("api2gn.var.config.parsers")
    return getattr(module, parsers[index])


def from_cd_nomenclature(column_name, mnemonique_type):
    return (column_name, mnemonique_type)
