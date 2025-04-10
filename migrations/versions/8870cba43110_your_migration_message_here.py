"""Your migration message here

Revision ID: 8870cba43110
Revises: b6fcc44916a8
Create Date: 2025-03-29 11:56:33.845355

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8870cba43110'
down_revision = 'b6fcc44916a8'
branch_labels = None
depends_on = None


def upgrade():
    # Define the new ENUM type
    userrole_enum = sa.Enum('member', 'GROUP_ADMIN', name='userrole')

    # Create the new ENUM type in the database
    userrole_enum.create(op.get_bind(), checkfirst=True)

    # Alter the column to use the new ENUM type with explicit casting and case conversion
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.execute(
            """
            ALTER TABLE users ALTER COLUMN role DROP DEFAULT;
            ALTER TABLE users ALTER COLUMN role TYPE userrole USING 
            CASE
                WHEN role::text = 'MEMBER' THEN 'member'
                WHEN role::text = 'GROUP_ADMIN' THEN 'GROUP_ADMIN'
                ELSE 'member'
            END::userrole;
            ALTER TABLE users ALTER COLUMN role SET DEFAULT 'member';
            """
        )

    # Drop the old ENUM type if it is no longer needed
    op.execute("DROP TYPE IF EXISTS user_role_enum")
    # ### end Alembic commands ###


def downgrade():
    # Recreate the ENUM type if it does not exist
    op.execute("""
    DO $$ 
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role_enum') THEN
            CREATE TYPE user_role_enum AS ENUM ('MEMBER', 'GROUP_ADMIN');
        END IF;
    END $$;
    """)

    # Alter the column back to the old ENUM type
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'role',
            existing_type=sa.Enum('member', 'GROUP_ADMIN', name='userrole'),
            type_=sa.Enum('MEMBER', 'GROUP_ADMIN', name='user_role_enum'),
            existing_nullable=False
        )
    # ### end Alembic commands ###
