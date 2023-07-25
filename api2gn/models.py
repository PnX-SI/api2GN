from geonature.utils.env import DB


class ParserModel(DB.Model):
    __tablename__ = "parser"
    __table_args__ = {"schema": "api2gn"}
    id = DB.Column(DB.Integer, primary_key=True)
    name = DB.Column(DB.Unicode)
    description = DB.Column(DB.Unicode)
    last_import = DB.Column(DB.DateTime)
    nb_row_total = DB.Column(DB.Integer)
    nb_row_last_import = DB.Column(DB.Integer)
    nb_row_last_import = DB.Column(DB.Integer)
    schedule_frequency = DB.Column(DB.Integer)
