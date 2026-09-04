"""Роль просмотра отчётов, SSO-алиасы пользователей."""
from alembic import op
import sqlalchemy as sa

revision = "015_reports_viewer_sso"
down_revision = "014_portal_roles"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT INTO roles (code, name) SELECT 'reports_viewer', 'Просмотр отчётов' "
            "WHERE NOT EXISTS (SELECT 1 FROM roles WHERE code = 'reports_viewer')"
        )
    )
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("sso_aliases", sa.String(512), nullable=True))


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("sso_aliases")
