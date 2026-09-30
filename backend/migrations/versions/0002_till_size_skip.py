"""Till mappings remember a size column and rows to leave out (voids, cancelled orders).

Three new columns on till_mappings, all optional, so existing remembered
layouts keep working and simply have none.

Revision ID: 0002_till_size_skip
Revises: 0001_baseline
Created: 2026-09-28
"""
from alembic import op
import sqlalchemy as sa


revision = '0002_till_size_skip'
down_revision = '0001_baseline'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('till_mappings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('size_column', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('skip_column', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('skip_values', sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table('till_mappings', schema=None) as batch_op:
        batch_op.drop_column('skip_values')
        batch_op.drop_column('skip_column')
        batch_op.drop_column('size_column')
