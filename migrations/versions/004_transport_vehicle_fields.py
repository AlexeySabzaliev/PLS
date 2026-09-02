"""Транспорт: операция, тягач/прицеп, документы ТС."""
import sqlalchemy as sa
from alembic import op

revision = "004_transport_vehicle_fields"
down_revision = "003_billing_rates"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("vehicle_operations", sa.Column("operation_type_code", sa.String(length=32), nullable=True))
    op.add_column("vehicle_operations", sa.Column("tractor_plate", sa.String(length=64), nullable=True))
    op.add_column("vehicle_operations", sa.Column("trailer_plate", sa.String(length=64), nullable=True))
    op.add_column("vehicle_operations", sa.Column("waybill_number", sa.String(length=256), nullable=True))
    op.add_column("vehicle_operations", sa.Column("mx1_number", sa.String(length=256), nullable=True))
    op.add_column("vehicle_operations", sa.Column("mx3_number", sa.String(length=256), nullable=True))
    op.add_column("vehicle_operations", sa.Column("seal_number", sa.String(length=128), nullable=True))
    op.add_column("vehicle_operations", sa.Column("torg2_number", sa.String(length=128), nullable=True))


def downgrade():
    for col in (
        "torg2_number",
        "seal_number",
        "mx3_number",
        "mx1_number",
        "waybill_number",
        "trailer_plate",
        "tractor_plate",
        "operation_type_code",
    ):
        op.drop_column("vehicle_operations", col)
