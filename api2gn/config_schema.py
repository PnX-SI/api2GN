from marshmallow import Schema, fields


class Api2GNSchema(Schema):
    PARSER_NUMBER_OF_TRIES = fields.Integer(load_default=5)
    PARSER_RETRY_SLEEP_TIME = fields.Integer(load_default=5)
    PARSER_RETRY_HTTP_STATUS = fields.List(fields.Integer(), load_default=[503])
