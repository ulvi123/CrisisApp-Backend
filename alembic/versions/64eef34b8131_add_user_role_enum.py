"""add_user_role_enum

Revision ID: 64eef34b8131
Revises: b48a72efa725
Create Date: 2024-10-31 08:31:01.764042

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from src.models import UserRole


# revision identifiers, used by Alembic.
revision: str = '64eef34b8131'
down_revision: Union[str, None] = 'b48a72efa725'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the Enum type
    user_role = sa.Enum(UserRole, name='userrole')
    user_role.create(op.get_bind(), checkfirst=True)

    # If you have existing data, first ensure it matches the enum values
    # Convert any NULL or invalid values to 'USER'
    op.execute("UPDATE user_tokens SET role = 'USER' WHERE role IS NULL OR role NOT IN ('USER', 'SUPPORT')")
    
    # Alter the column type
    with op.batch_alter_table('user_tokens') as batch_op:
        batch_op.alter_column('role',
                            existing_type=sa.String(250),
                            type_=sa.Enum(UserRole),
                            existing_nullable=True,
                            postgresql_using="role::userrole")


def downgrade() -> None:
    # Convert back to string type
    with op.batch_alter_table('user_tokens') as batch_op:
        batch_op.alter_column('role',
                            type_=sa.String(250),
                            existing_type=sa.Enum(UserRole),
                            existing_nullable=True)

    # Drop the enum type
    op.execute('DROP TYPE userrole')

