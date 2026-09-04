"""Количество пакетов документов на строку ТС (строки ПРР при импорте)."""
import sqlalchemy as sa
from alembic import op

revision = "018_vehicle_billing_doc_qty"
down_revision = "017_vehicle_ops_audit"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("vehicle_operations") as batch_op:
        batch_op.add_column(
            sa.Column("billing_document_qty", sa.Integer(), nullable=False, server_default="1"),
        )


def downgrade():
    with op.batch_alter_table("vehicle_operations") as batch_op:
        batch_op.drop_column("billing_document_qty")
