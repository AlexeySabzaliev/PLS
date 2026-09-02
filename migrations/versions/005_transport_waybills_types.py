"""Типы ТС, накладные vehicle_waybills, импорт с охраны."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "005_transport_waybills_types"
down_revision = "004_transport_vehicle_fields"
branch_labels = None
depends_on = None

_VEHICLE_TYPES = [
    ("truck", "Фура (тягач + полуприцеп)", 10),
    ("gazelle", "Газель", 20),
    ("van", "Фургон", 30),
    ("container", "Контейнеровоз", 40),
    ("tent", "Тентованный", 50),
    ("refrigerator", "Рефрижератор", 60),
    ("other", "Прочее", 99),
]


def _table_names(bind) -> set[str]:
    return set(inspect(bind).get_table_names())


def _column_names(bind, table: str) -> set[str]:
    return {c["name"] for c in inspect(bind).get_columns(table)}


def upgrade():
    bind = op.get_bind()
    tables = _table_names(bind)

    if "vehicle_types" not in tables:
        vehicle_types = op.create_table(
            "vehicle_types",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.UniqueConstraint("code"),
        )
        op.bulk_insert(
            vehicle_types,
            [{"code": c, "name": n, "sort_order": s} for c, n, s in _VEHICLE_TYPES],
        )
    elif bind.execute(sa.text("SELECT COUNT(*) FROM vehicle_types")).scalar() == 0:
        op.bulk_insert(
            sa.table(
                "vehicle_types",
                sa.column("code", sa.String),
                sa.column("name", sa.String),
                sa.column("sort_order", sa.Integer),
            ),
            [{"code": c, "name": n, "sort_order": s} for c, n, s in _VEHICLE_TYPES],
        )

    if "vehicle_waybills" not in tables:
        op.create_table(
            "vehicle_waybills",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "vehicle_operation_id",
                sa.Integer(),
                sa.ForeignKey("vehicle_operations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("waybill_number", sa.String(length=256)),
            sa.Column("mx_number", sa.String(length=256)),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        )
        op.create_index("ix_vehicle_waybills_op", "vehicle_waybills", ["vehicle_operation_id", "sort_order"])

    vo_cols = _column_names(bind, "vehicle_operations")
    if "vehicle_type_id" not in vo_cols:
        op.add_column("vehicle_operations", sa.Column("vehicle_type_id", sa.Integer(), nullable=True))
    if "source" not in vo_cols:
        op.add_column(
            "vehicle_operations",
            sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"),
        )
    if "security_request_id" not in vo_cols:
        op.add_column("vehicle_operations", sa.Column("security_request_id", sa.String(length=64), nullable=True))

    if "vehicle_waybills" in _table_names(bind):
        existing_ops = {
            r[0]
            for r in bind.execute(sa.text("SELECT DISTINCT vehicle_operation_id FROM vehicle_waybills")).fetchall()
        }
        rows = bind.execute(
            sa.text(
                """
                SELECT id, operation_type_code, waybill_number, mx1_number, mx3_number
                FROM vehicle_operations
                WHERE waybill_number IS NOT NULL AND TRIM(waybill_number) != ''
                """
            )
        ).fetchall()
        for row in rows:
            if row.id in existing_ops:
                continue
            op_type = (row.operation_type_code or "inbound").strip()
            mx = row.mx3_number if op_type == "outbound" else row.mx1_number
            bind.execute(
                sa.text(
                    """
                    INSERT INTO vehicle_waybills (vehicle_operation_id, waybill_number, mx_number, sort_order)
                    VALUES (:op_id, :wb, :mx, 0)
                    """
                ),
                {"op_id": row.id, "wb": row.waybill_number, "mx": mx},
            )


def downgrade():
    bind = op.get_bind()
    tables = _table_names(bind)
    vo_cols = _column_names(bind, "vehicle_operations") if "vehicle_operations" in tables else set()

    if "security_request_id" in vo_cols:
        op.drop_column("vehicle_operations", "security_request_id")
    if "source" in vo_cols:
        op.drop_column("vehicle_operations", "source")
    if "vehicle_type_id" in vo_cols:
        op.drop_column("vehicle_operations", "vehicle_type_id")
    if "vehicle_waybills" in tables:
        op.drop_index("ix_vehicle_waybills_op", table_name="vehicle_waybills")
        op.drop_table("vehicle_waybills")
    if "vehicle_types" in tables:
        op.drop_table("vehicle_types")
