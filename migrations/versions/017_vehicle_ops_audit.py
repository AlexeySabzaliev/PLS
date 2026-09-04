"""Статус строки ТС, обработка и журнал изменений."""
import sqlalchemy as sa
from alembic import op

revision = "017_vehicle_ops_audit"
down_revision = "016_password_reset"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return any(c["name"] == column for c in insp.get_columns(table))


def _has_table(table: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return table in insp.get_table_names()


def upgrade():
    if not _has_column("vehicle_operations", "arrival_status"):
        with op.batch_alter_table("vehicle_operations") as batch_op:
            batch_op.add_column(
                sa.Column("arrival_status", sa.String(length=32), nullable=False, server_default="expected"),
            )
    if not _has_column("vehicle_operations", "processed_by"):
        with op.batch_alter_table("vehicle_operations") as batch_op:
            batch_op.add_column(sa.Column("processed_by", sa.Integer(), nullable=True))
    if not _has_column("vehicle_operations", "processed_at"):
        with op.batch_alter_table("vehicle_operations") as batch_op:
            batch_op.add_column(sa.Column("processed_at", sa.DateTime(), nullable=True))

    bind = op.get_bind()
    insp = sa.inspect(bind)
    fks = {fk["name"] for fk in insp.get_foreign_keys("vehicle_operations")}
    if "fk_vehicle_operations_processed_by" not in fks:
        with op.batch_alter_table("vehicle_operations") as batch_op:
            batch_op.create_foreign_key(
                "fk_vehicle_operations_processed_by",
                "users",
                ["processed_by"],
                ["id"],
            )

    if not _has_table("vehicle_operation_audit_logs"):
        op.create_table(
            "vehicle_operation_audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("vehicle_operation_id", sa.Integer(), sa.ForeignKey("vehicle_operations.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("user_name", sa.String(length=255), nullable=True),
            sa.Column("action", sa.String(length=64), nullable=False),
            sa.Column("changes", sa.JSON(), nullable=True),
            sa.Column("snapshot", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index(
            "ix_vehicle_operation_audit_vehicle_id",
            "vehicle_operation_audit_logs",
            ["vehicle_operation_id"],
        )


def downgrade():
    if _has_table("vehicle_operation_audit_logs"):
        op.drop_index("ix_vehicle_operation_audit_vehicle_id", table_name="vehicle_operation_audit_logs")
        op.drop_table("vehicle_operation_audit_logs")
    bind = op.get_bind()
    insp = sa.inspect(bind)
    fks = {fk["name"] for fk in insp.get_foreign_keys("vehicle_operations")}
    if "fk_vehicle_operations_processed_by" in fks:
        with op.batch_alter_table("vehicle_operations") as batch_op:
            batch_op.drop_constraint("fk_vehicle_operations_processed_by", type_="foreignkey")
    if _has_column("vehicle_operations", "processed_at"):
        with op.batch_alter_table("vehicle_operations") as batch_op:
            batch_op.drop_column("processed_at")
    if _has_column("vehicle_operations", "processed_by"):
        with op.batch_alter_table("vehicle_operations") as batch_op:
            batch_op.drop_column("processed_by")
    if _has_column("vehicle_operations", "arrival_status"):
        with op.batch_alter_table("vehicle_operations") as batch_op:
            batch_op.drop_column("arrival_status")
