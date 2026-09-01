"""Initial schema for PLS portal."""
from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Таблицы создаются через db.create_all / flask db migrate в dev.
    # Заглушка ревизии для Alembic; при первом deploy: flask db migrate -m "initial"
    pass


def downgrade():
    pass
