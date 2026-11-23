"""GN permission 2.13

Revision ID: e27e2994d3bd
Revises: 42732da3363e
Create Date: 2023-08-11 12:22:46.425506

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e27e2994d3bd"
down_revision = "42732da3363e"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        INSERT INTO gn_permissions.t_objects
        (code_object, description_object)
        VALUES
        ('PARSER', 'Gestion des parser dans le backoffice')
        ;

        INSERT INTO gn_commons.t_modules
        (module_code, module_label, module_desc, module_external_url, active_frontend, active_backend)
        VALUES('API2GN', 'Api2GN', 'Module API2GN', '_blank', false, false) ON CONFLICT DO NOTHING;

        INSERT INTO
                gn_permissions.t_permissions_available (
                    id_module,
                    id_object,
                    id_action,
                    scope_filter,
                    label
                )
            SELECT
                m.id_module,
                o.id_object,
                a.id_action,
                v.scope_filter,
                v.label
            FROM (
                    VALUES
                    ('API2GN', 'PARSER', 'R', False, 'Voir les parsers')
                    ,('API2GN', 'PARSER', 'U', False, 'Modifier les parser')
                    ,('API2GN', 'PARSER', 'C', False, 'Créer des parser')
                    ,('API2GN', 'PARSER', 'D', False, 'Supprimer des parsers')

                ) AS v (module_code, object_code, action_code, scope_filter, label)
            JOIN
                gn_commons.t_modules m ON m.module_code = v.module_code
            JOIN
                gn_permissions.t_objects o ON o.code_object = v.object_code
            JOIN
                gn_permissions.bib_actions a ON a.code_action = v.action_code

    """
    )


def downgrade():
    op.execute(
        """
        DELETE FROM gn_permissions.t_permissions  WHERE id_module  = (SELECT id_module FROM gn_commons.t_modules WHERE module_code = 'API2GN') OR id_object =  (SELECT id_object FROM  gn_permissions.t_objects WHERE code_object = 'PARSER') ;
        DELETE FROM gn_permissions.t_permissions_available WHERE id_object = (SELECT id_object FROM  gn_permissions.t_objects WHERE code_object = 'PARSER');
        DELETE FROM  gn_permissions.t_objects where code_object = 'PARSER';
        DELETE FROM  gn_commons.t_modules where module_code = 'API2GN';
        """
    )
