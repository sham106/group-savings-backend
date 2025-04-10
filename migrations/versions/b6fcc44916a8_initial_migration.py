"""Initial migration

Revision ID: b6fcc44916a8
Revises: 
Create Date: 2025-03-29 11:03:37.145032

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b6fcc44916a8'
down_revision = None
branch_labels = None
depends_on = None


role_enum = sa.Enum('admin', 'member', name='user_role_enum')

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
     op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('username', sa.String(50), unique=True, nullable=False),
        sa.Column('email', sa.String(120), unique=True, nullable=False),
        sa.Column('password', sa.String(255), nullable=False),
        sa.Column('role', role_enum, nullable=False, server_default='member'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('users')

    # ### end Alembic commands ###
