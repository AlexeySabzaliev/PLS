"""Ставки и billing_config для биллинга."""
from alembic import op
import sqlalchemy as sa

revision = "003_billing_rates"
down_revision = "002_tariff_billing_sso"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tariff_rules", sa.Column("rate_ex_vat", sa.Numeric(14, 4), nullable=True))
    op.add_column("tariff_rules", sa.Column("formula", sa.String(length=64), nullable=True))
    op.add_column("contracts", sa.Column("billing_config", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("contracts", "billing_config")
    op.drop_column("tariff_rules", "formula")
    op.drop_column("tariff_rules", "rate_ex_vat")
