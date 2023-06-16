from flask import Blueprint

from api2gn.commands import cmd_list_parsers, run

blueprint = Blueprint("parser", __name__)

blueprint.cli.add_command(cmd_list_parsers)
blueprint.cli.add_command(run)

from api2gn.admin import *
