"""Автопролонгация договоров и ДС."""
from alembic import op
import sqlalchemy as sa

revision = "013_contract_auto_renew"
down_revision = "012_warehouse_work_hours"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "contracts",
        sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "contract_amendments",
        sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade():
    op.drop_column("contract_amendments", "auto_renew")
    op.drop_column("contracts", "auto_renew")
