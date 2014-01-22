"""Extended rev field to 15 from 12

Revision ID: 2e5b55e88528
Revises: 5150d83199e0
Create Date: 2014-01-22 15:46:56.235345

"""

from sqlalchemy import String

# revision identifiers, used by Alembic.
revision = '2e5b55e88528'
down_revision = '5150d83199e0'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('dropbox_store', 'source_file_rev', type_=String(15))

def downgrade():
    op.alter_column('dropbox_store', 'source_file_rev', type_=String(11))
