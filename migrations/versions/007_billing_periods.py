"""Биллинговые периоды и блокировка правок."""
from alembic import op
import sqlalchemy as sa

revision = "007_billing_periods"
down_revision = "006_vehicle_type_dimensions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "billing_periods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("period_month", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("total_ex_vat", sa.Numeric(14, 2), nullable=True),
        sa.Column("locked_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "contract_id", "period_year", "period_month",
            name="uq_billing_period_contract_ym",
        ),
    )
    op.create_index(
        "ix_billing_periods_contract_ym",
        "billing_periods",
        ["contract_id", "period_year", "period_month"],
    )


def downgrade():
    op.drop_index("ix_billing_periods_contract_ym", table_name="billing_periods")
    op.drop_table("billing_periods")
