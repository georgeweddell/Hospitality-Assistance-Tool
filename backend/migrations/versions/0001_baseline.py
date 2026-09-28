"""Baseline: the schema as it was on 28 Sep 2026, before Alembic.

Every database made before then was built by create_all from models.py, so
there's nothing to do: migrate.py marks those databases as being at this
revision, and later migrations start from here.

Revision ID: 0001_baseline
Revises:
Created: 2026-09-28
"""

revision = '0001_baseline'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
