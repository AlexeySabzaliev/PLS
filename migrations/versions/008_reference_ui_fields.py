"""Справочники: is_active для типов продукта и единиц, файл ДС."""
from alembic import op
import sqlalchemy as sa

revision = "008_reference_ui_fields"
down_revision = "007_billing_periods"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "product_types",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "units_of_measure",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "contract_amendments",
        sa.Column("source_file_path", sa.String(length=512), nullable=True),
    )
    # Неиспользуемые типы продукта и единицы — неактивны по умолчанию
    op.execute(
        "UPDATE product_types SET is_active = 0 "
        "WHERE code IN ('SUBLEASE', 'RENT')"
    )
    op.execute(
        "UPDATE units_of_measure SET is_active = 0 "
        "WHERE code IN ('m2day', 'vehicle')"
    )


def downgrade():
    op.drop_column("contract_amendments", "source_file_path")
    op.drop_column("units_of_measure", "is_active")
    op.drop_column("product_types", "is_active")
