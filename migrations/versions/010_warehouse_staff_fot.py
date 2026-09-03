"""Штат ФОТ по складам (для отчёта ФОТ vs операционка)."""
from alembic import op
import sqlalchemy as sa

revision = "010_warehouse_staff_fot"
down_revision = "009_section_maintenance"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "warehouse_staff_positions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("monthly_rate", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("headcount", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("headcount > 0", name="ck_staff_positions_headcount"),
    )
    op.create_index(
        "ix_staff_positions_wh",
        "warehouse_staff_positions",
        ["warehouse_id", "sort_order"],
    )

    op.create_table(
        "warehouse_staff_position_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("position_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("monthly_rate", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("headcount", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["position_id"], ["warehouse_staff_positions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_staff_pos_versions_dates",
        ),
    )
    op.create_index(
        "ix_staff_pos_versions_wh_dates",
        "warehouse_staff_position_versions",
        ["warehouse_id", "valid_from", "valid_to"],
    )


def downgrade():
    op.drop_table("warehouse_staff_position_versions")
    op.drop_table("warehouse_staff_positions")
