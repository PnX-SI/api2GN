from marshmallow import Schema, fields


class Api2GNSchema(Schema):
    PARSER_NUMBER_OF_TRIES = fields.Integer(missing=5)
