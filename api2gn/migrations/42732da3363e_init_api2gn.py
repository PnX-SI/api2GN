"""init api2gn

Revision ID: 5b334b77f5f5
Revises: 830cc8f4daef
Create Date: 2021-09-21 13:22:45.003976

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "42732da3363e"
down_revision = None
branch_labels = ("api2gn",)
depends_on = None


def upgrade():
    op.execute(
        """
            CREATE SCHEMA api2gn;
            CREATE TABLE api2gn.parser (
                id SERIAL NOT NULL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description text,
                last_import timestamp,
                nb_row_total integer,
                nb_row_last_import integer,
                schedule_frequency integer
            );
        """
    )


def downgrade():
    op.execute(
        """
            DROP SCHEMA api2gn CASCADE;
        """
    )
