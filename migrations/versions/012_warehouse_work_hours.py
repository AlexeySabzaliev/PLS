"""График работы склада (для сверхурочных и биллинга)."""
from alembic import op
import sqlalchemy as sa

revision = "012_warehouse_work_hours"
down_revision = "011_import_registry"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "warehouses",
        sa.Column("work_day_start", sa.Time(), nullable=False, server_default="09:00:00"),
    )
    op.add_column(
        "warehouses",
        sa.Column("work_day_end", sa.Time(), nullable=False, server_default="17:30:00"),
    )


def downgrade():
    op.drop_column("warehouses", "work_day_end")
    op.drop_column("warehouses", "work_day_start")
