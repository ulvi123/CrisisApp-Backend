"""Make end_time column NOT NULL

Revision ID: 603192a121f4
Revises: b4e9ce414cb8
Create Date: 2024-07-16 23:27:09.910812

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '603192a121f4'
down_revision: Union[str, None] = 'b4e9ce414cb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Set a default value for existing NULL end_time values
    op.execute("UPDATE service_incidents SET end_time = '2024-01-01 00:00:00' WHERE end_time IS NULL")

    # Alter the column to be NOT NULL
    op.alter_column('service_incidents', 'end_time', existing_type=sa.DateTime(), nullable=False)

def downgrade():
    # Revert the column to allow NULL values
    op.alter_column('service_incidents', 'end_time', existing_type=sa.DateTime(), nullable=True)