"""agent schema

Revision ID: df04bd0609a8
Revises: 
Create Date: 2026-11-09 14:30:36.990200

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df04bd0609a8'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Creates the custom schema if it doesn't already exist
    op.execute("CREATE SCHEMA IF NOT EXISTS agent")

def downgrade() -> None:
    # Drops the schema and all its associated tables
    op.execute("DROP SCHEMA IF EXISTS agent CASCADE")