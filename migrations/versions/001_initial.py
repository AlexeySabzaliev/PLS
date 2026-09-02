"""Initial schema for PLS portal."""
from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("security_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "warehouses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("security_visit_place", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "product_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "units_of_measure",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "staff_positions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "vehicle_plates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plate_number", sa.String(length=32), nullable=False),
        sa.Column("vehicle_type", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plate_number"),
    )

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "contracts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("product_type_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["product_type_id"], ["product_types.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "process_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("base_process", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "section_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("section_code", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "section_code", name="uq_section_permissions_role_section"),
    )

    op.create_table(
        "user_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )

    op.create_table(
        "user_warehouse_access",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "warehouse_id", name="uq_user_warehouse_access"),
    )

    op.create_table(
        "contract_amendments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contract_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "process_line_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("process_line_id", sa.Integer(), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["process_line_id"], ["process_lines.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("process_line_id"),
    )

    op.create_table(
        "tariff_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contract_id", sa.Integer(), nullable=False),
        sa.Column("amendment_id", sa.Integer(), nullable=False),
        sa.Column("billing_line_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=True),
        sa.Column("report_role", sa.String(length=64), nullable=True),
        sa.Column("report_scope", sa.String(length=64), nullable=True),
        sa.Column("quantity_source", sa.String(length=64), nullable=True),
        sa.Column("is_custom", sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column("price_agreed", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["amendment_id"], ["contract_amendments.id"]),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["units_of_measure.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "vehicle_operations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contract_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("operation_date", sa.Date(), nullable=False),
        sa.Column("plate_number", sa.String(length=32), nullable=True),
        sa.Column("volume_document_m3", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("handling_type_code", sa.String(length=32), nullable=True),
        sa.Column("extra_handling_m3", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("extra_document_set_qty", sa.Integer(), nullable=True),
        sa.Column("registered_at", sa.DateTime(), nullable=True),
        sa.Column("departed_at", sa.DateTime(), nullable=True),
        sa.Column("report_quantities", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_vehicle_operations_wh_date",
        "vehicle_operations",
        ["warehouse_id", "operation_date"],
    )

    op.create_table(
        "operation_daily_totals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contract_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("billing_line_code", sa.String(length=64), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=3), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "contract_id", "report_date", "billing_line_code",
            name="uq_operation_daily_totals_contract_date_code",
        ),
    )
    op.create_index(
        "ix_operation_daily_totals_wh_date",
        "operation_daily_totals",
        ["warehouse_id", "report_date"],
    )

    op.create_table(
        "shift_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("area_entries", sa.JSON(), nullable=True),
        sa.Column("extra_entries", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("warehouse_id", "report_date", name="uq_shift_reports_wh_date"),
    )

    op.create_table(
        "shift_day_confirmations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("report_role", sa.String(length=64), nullable=False),
        sa.Column("confirmed_by", sa.Integer(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "warehouse_id", "report_date", "report_role",
            name="uq_shift_day_confirm_wh_date_role",
        ),
    )
    op.create_index(
        "ix_shift_day_confirm_wh_date",
        "shift_day_confirmations",
        ["warehouse_id", "report_date"],
    )


def downgrade():
    op.drop_table("shift_day_confirmations")
    op.drop_table("shift_reports")
    op.drop_table("operation_daily_totals")
    op.drop_table("vehicle_operations")
    op.drop_table("tariff_rules")
    op.drop_table("process_line_config")
    op.drop_table("contract_amendments")
    op.drop_table("user_warehouse_access")
    op.drop_table("user_roles")
    op.drop_table("section_permissions")
    op.drop_table("process_lines")
    op.drop_table("contracts")
    op.drop_table("users")
    op.drop_table("roles")
    op.drop_table("vehicle_plates")
    op.drop_table("staff_positions")
    op.drop_table("units_of_measure")
    op.drop_table("product_types")
    op.drop_table("warehouses")
    op.drop_table("clients")
