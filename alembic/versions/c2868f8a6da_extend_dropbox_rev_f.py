"""extend dropbox_rev field

Revision ID: c2868f8a6da
Revises: 377b449f1482
Create Date: 2014-01-23 01:58:07.966938

"""

from sqlalchemy import String

# revision identifiers, used by Alembic.
revision = 'c2868f8a6da'
down_revision = '377b449f1482'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('ivle_file', 'dropbox_rev', type_=String(15))

def downgrade():
    op.alter_column('ivle_file', 'dropbox_rev', type_=String(11))
