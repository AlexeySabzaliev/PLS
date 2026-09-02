"""Габариты в справочнике типов ТС."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "006_vehicle_type_dimensions"
down_revision = "005_transport_waybills_types"
branch_labels = None
depends_on = None

_DEFAULT_DIMS = {
    "truck": "13,6×2,45×2,70",
    "gazelle": "6,0×2,1×2,2",
    "van": "4,2×2,0×2,2",
    "container": "13,6×2,45×2,70",
    "tent": "13,6×2,45×2,70",
    "refrigerator": "13,6×2,45×2,70",
}


def upgrade():
    bind = op.get_bind()
    cols = {c["name"] for c in inspect(bind).get_columns("vehicle_types")}
    if "dimensions_label" not in cols:
        op.add_column("vehicle_types", sa.Column("dimensions_label", sa.String(length=128), nullable=True))
    for code, dims in _DEFAULT_DIMS.items():
        bind.execute(
            sa.text(
                "UPDATE vehicle_types SET dimensions_label = :dims "
                "WHERE code = :code AND (dimensions_label IS NULL OR dimensions_label = '')"
            ),
            {"code": code, "dims": dims},
        )


def downgrade():
    bind = op.get_bind()
    cols = {c["name"] for c in inspect(bind).get_columns("vehicle_types")}
    if "dimensions_label" in cols:
        op.drop_column("vehicle_types", "dimensions_label")
