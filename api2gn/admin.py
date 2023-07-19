from flask_admin.contrib.sqla import ModelView

from geonature.core.admin.admin import admin
from geonature.utils.env import db

from api2gn.models import ParserModel


class Api2GNAdmin(ModelView):
    column_list = ("name", "last_import", "type")
    can_edit = False
    can_delete = False


admin.add_view(Api2GNAdmin(ParserModel, db.session, category="Api2GN", name="Parsers"))
