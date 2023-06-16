from geonature.utils.env import DB


class ParserModel(DB.Model):
    __tablename__ = "parser"
    __table_args__ = {"schema": "api2gn"}
    id = DB.Column(DB.Integer, primary_key=True)
    name = DB.Column(DB.Unicode)
    type = DB.Column(DB.Unicode)
    last_import = DB.Column(DB.DateTime)
