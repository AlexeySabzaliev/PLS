"""Заявки на восстановление пароля."""
from alembic import op
import sqlalchemy as sa

revision = "016_password_reset"
down_revision = "015_reports_viewer_sso"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "password_reset_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("user_note", sa.String(512), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("admin_note", sa.String(512), nullable=True),
    )


def downgrade():
    op.drop_table("password_reset_requests")
