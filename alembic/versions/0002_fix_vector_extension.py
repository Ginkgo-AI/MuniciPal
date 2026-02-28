"""Fix pgvector extension name to 'vector'.

The pgvector project installs as the 'vector' extension, not 'pgvector'.
The original 0001 migration used the wrong name. This migration ensures
the correct extension is available for databases that already ran 0001.

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-28

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))


def downgrade() -> None:
    pass
