"""Реестр импорта из Billings (import_registry)."""
from alembic import op
import sqlalchemy as sa

revision = "011_import_registry"
down_revision = "010_warehouse_staff_fot"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "import_registry",
        sa.Column("entity_type", sa.String(64), primary_key=True),
        sa.Column("entity_key", sa.String(255), primary_key=True),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.Column("billings_id", sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_table("import_registry")
