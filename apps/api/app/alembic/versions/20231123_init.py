# Alembic Initial Migration: Extensions and Schema

"""Initial migration creating PostgreSQL extensions and table schemas."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from hireloop.apps.api.app.models.models import Base

# Revision identifiers
revision = "20231123_init"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    conn = op.get_bind()
    # 1. Enable required PostgreSQL extensions
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))

    # 2. Create all tables & indexes defined in models
    Base.metadata.create_all(bind=conn)

def downgrade() -> None:
    conn = op.get_bind()
    Base.metadata.drop_all(bind=conn)
