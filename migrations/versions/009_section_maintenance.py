"""Заглушки разделов (section_maintenance)."""
from alembic import op
import sqlalchemy as sa

revision = "009_section_maintenance"
down_revision = "008_reference_ui_fields"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "section_maintenance",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("target_key", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("target_type", "target_key"),
    )


def downgrade():
    op.drop_table("section_maintenance")
