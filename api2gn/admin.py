from flask_admin.contrib.sqla import ModelView

from geonature.core.admin.admin import admin
from geonature.core.admin.utils import CruvedProtectedMixin
from geonature.utils.env import db

from api2gn.models import ParserModel


class Api2GNAdmin(ModelView):
    module_code = "ADMIN"
    object_code = "PARSER"
    column_list = (
        "name",
        "description",
        "last_import",
        "nb_row_total",
        "nb_row_last_import",
        "schedule_frequency",
    )
    column_labels = dict(
        name="Nom du parser",
        description="Description",
        last_import="Dernier import",
        nb_row_total="Nombre total importé",
        nb_row_last_import="Nombre au dernier import",
        schedule_frequency="Fréquence de MAJ (en jour)",
    )
    form_columns = (
        "name",
        "schedule_frequency",
    )


admin.add_view(Api2GNAdmin(ParserModel, db.session, category="Api2GN", name="Parsers"))
