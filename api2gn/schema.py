import sys

import click

from sqlalchemy import inspect
from sqlalchemy.sql.schema import Column
from geonature.core.gn_synthese.models import Synthese


class ValidationError(Exception):
    pass


class MappingValidator:
    def __init__(self, schema):
        self.schema = schema

    def validate(self, **kwargs):
        mapper = inspect(Synthese)
        # for c in mapper.columns:
        #     print(dir(c))
        not_null_synthese_col = set(
            [
                col.key
                for col in mapper.columns
                if type(col) is Column
                and col.nullable is False
                and col.primary_key is False
            ]
        )
        all_synthese_cols = set([col.key for col in mapper.columns])
        mapping_cols = set([key for key, value in self.schema.items()])
        # validate if mapping columns exist in synthese
        not_existing_cols = mapping_cols - all_synthese_cols
        if not_existing_cols:
            click.secho(
                f"The value(s) {not_existing_cols} does not exist in Synthese", fg="red"
            )
            sys.exit()
        missing_required_cols = not_null_synthese_col - mapping_cols
        if missing_required_cols:
            click.secho(
                f"These columns are missing from your mapping : {missing_required_cols}",
                fg="red",
            )
            sys.exit()
