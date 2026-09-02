"""Ставки: привязка к тарифу биллинга; заявки SSO."""
from alembic import op
import sqlalchemy as sa

revision = "002_tariff_billing_sso"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "tariff_rules",
        sa.Column("rate_line_code", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "tariff_rules",
        sa.Column(
            "quantity_divisor",
            sa.Numeric(precision=12, scale=3),
            nullable=False,
            server_default="1",
        ),
    )

    op.create_table(
        "sso_access_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("raw_identity", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("login_attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by", sa.Integer(), nullable=True),
        sa.Column("admin_note", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )


def downgrade():
    op.drop_table("sso_access_requests")
    op.drop_column("tariff_rules", "quantity_divisor")
    op.drop_column("tariff_rules", "rate_line_code")
