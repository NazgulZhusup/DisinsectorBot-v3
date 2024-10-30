"""Initial migration with updated Admin model

Revision ID: 0c335ee0b1ad
Revises: 
Create Date: 2024-10-29 13:39:46.647770

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0c335ee0b1ad'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('admins',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=100), nullable=False),
    sa.Column('password', sa.String(length=200), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('email', name='uq_admin_email')
    )
    op.create_table('clients',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('address', sa.String(length=200), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('phone', name='uq_client_phone')
    )
    op.create_table('disinsectors',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=100), nullable=False),
    sa.Column('password', sa.String(length=200), nullable=False),
    sa.Column('token', sa.String(length=100), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email', name='uq_disinsector_email'),
    sa.UniqueConstraint('token', name='uq_disinsector_token')
    )
    op.create_table('orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=False),
    sa.Column('disinsector_id', sa.Integer(), nullable=True),
    sa.Column('order_status', sa.String(length=50), nullable=False),
    sa.Column('object_type', sa.String(length=100), nullable=False),
    sa.Column('insect_quantity', sa.String(length=50), nullable=False),
    sa.Column('disinsect_experience', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
    sa.ForeignKeyConstraint(['disinsector_id'], ['disinsectors.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('orders')
    op.drop_table('disinsectors')
    op.drop_table('clients')
    op.drop_table('admins')
    # ### end Alembic commands ###
