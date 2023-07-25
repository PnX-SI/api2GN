from flask import Blueprint

from api2gn.commands import cmd_list_parsers, run

blueprint = Blueprint("parser", __name__)

blueprint.cli.add_command(cmd_list_parsers)
blueprint.cli.add_command(run)

from api2gn.admin import *


import click

from tqdm import tqdm

from time import sleep


@blueprint.cli.command()
def test():
    pbar = tqdm(total=100)
    for i in range(10):
        sleep(0.1)
        pbar.update(10)
    pbar.close()
