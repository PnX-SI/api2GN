from flask import Blueprint


blueprint = Blueprint("api2gn", __name__)

from api2gn.admin import *
