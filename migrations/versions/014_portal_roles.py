"""Роли портала: специалист ВЭД, снятие руководителя смены с пользователей."""
from alembic import op
import sqlalchemy as sa

revision = "014_portal_roles"
down_revision = "013_contract_auto_renew"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT INTO roles (code, name) SELECT 'ved_specialist', 'Специалист ВЭД' "
            "WHERE NOT EXISTS (SELECT 1 FROM roles WHERE code = 'ved_specialist')"
        )
    )
    conn.execute(
        sa.text(
            "DELETE FROM user_roles WHERE role_id IN (SELECT id FROM roles WHERE code = 'supervisor')"
        )
    )


def downgrade():
    pass
