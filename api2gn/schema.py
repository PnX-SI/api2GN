from marshmallow import Schema, fields


class SyntheseSchema(Schema):
    cd_nom = fields.String(required=True)
    observers = fields.String(required=True)
    date_min = fields.String(required=True)
    date_max = fields.String(required=True)
    the_geom_4326 = fields.String()
    the_geom_local = fields.String()
    id_dataset = fields.String(required=True)
    id_source = fields.String(required=True)
    nom_cite = fields.String(required=True)


class WFSSchema(Schema):
    layer = fields.String()
    version = fields.String()


class ImportSchema(Schema):
    # TODO : custom validator to check no multiple :
    url = fields.String(required=True)
    type = fields.String(required=True)
    geometry_col = fields.String()
    mapping = fields.Nested(SyntheseSchema)
    wfs = fields.Nested(WFSSchema)
    limit = fields.Integer(missing=50)
