from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text


# revision identifiers, used by Alembic
revision = 'ba007040d77d'
down_revision = '8870cba43110'
branch_labels = None
depends_on = None

def upgrade():
    transaction_type_enum = postgresql.ENUM('CONTRIBUTION', 'WITHDRAWAL', name='transactiontype', create_type=False)
    
    # Check if ENUM exists before creating
    conn = op.get_bind()
    result = conn.execute(text("SELECT 1 FROM pg_type WHERE typname = 'transactiontype'"))
    
    if result.fetchone() is None:
        transaction_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Now create the transactions table
    op.create_table('transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('transaction_type', transaction_type_enum, nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('transactions')

    # Drop ENUM only if it exists
    op.execute("""
    DO $$ 
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'transactiontype') THEN
            DROP TYPE transactiontype;
        END IF;
    END $$;
    """)
