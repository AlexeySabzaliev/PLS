"""Заявки на перевозку УЗнТ (транспорт_requests)."""
import sqlalchemy as sa
from alembic import op

revision = "019_uznt_requests"
down_revision = "018_vehicle_billing_doc_qty"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "transport_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("number", sa.String(length=64), nullable=False),
        sa.Column("request_date", sa.Date(), nullable=False),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("from_location", sa.String(length=255)),
        sa.Column("to_location", sa.String(length=255)),
        sa.Column("cargo_name", sa.String(length=255)),
        sa.Column("cargo_volume_m3", sa.Numeric(12, 3)),
        sa.Column("cargo_weight_t", sa.Numeric(12, 3)),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False, server_default="1"),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default="pcs"),
        sa.Column("vehicle_type_id", sa.Integer(), sa.ForeignKey("vehicle_types.id")),
        sa.Column("trucks_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("price", sa.Numeric(14, 2)),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="new"),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="normal"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_transport_requests_number", "transport_requests", ["number"], unique=True)
    op.create_index("ix_transport_requests_request_date", "transport_requests", ["request_date"])


def downgrade():
    op.drop_index("ix_transport_requests_number", table_name="transport_requests")
    op.drop_index("ix_transport_requests_request_date", table_name="transport_requests")
    op.drop_table("transport_requests")