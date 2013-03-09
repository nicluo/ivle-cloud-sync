"""remove history table

Revision ID: 4fbd229dbae6
Revises: 2046ba892660
Create Date: 2013-02-24 11:28:49.920000

"""

# revision identifiers, used by Alembic.
revision = '4fbd229dbae6'
down_revision = '2046ba892660'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table(u'dropbox_upload_history')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table(u'dropbox_upload_history',
    sa.Column(u'history_id', mysql.INTEGER(display_width=11), nullable=False),
    sa.Column(u'job_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True),
    sa.Column(u'file_id', mysql.VARCHAR(length=36), nullable=True),
    sa.Column(u'http_url', mysql.VARCHAR(length=1024), nullable=True),
    sa.Column(u'method', mysql.VARCHAR(length=4), nullable=True),
    sa.Column(u'user_id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True),
    sa.Column(u'target_path', mysql.VARCHAR(length=256), nullable=True),
    sa.Column(u'upload_timestamp', sa.DATETIME(), nullable=True),
    sa.PrimaryKeyConstraint(u'history_id')
    )
    ### end Alembic commands ###
