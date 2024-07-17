"""create incident table

Revision ID: 2602ce9136ef
Revises: 
Create Date: 2024-07-09 10:58:44.325557

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2602ce9136ef'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'service_incidents',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('affected_products', postgresql.ARRAY(sa.String(50)), nullable=False), #Array converted 
        sa.Column('severity', sa.String(50), nullable=False),
        sa.Column('suspected_owning_team', postgresql.ARRAY(sa.String), nullable=False),#Array converted 
        sa.Column('start_time', sa.DateTime, nullable=False),  # Changed to DateTime
        sa.Column('end_time', sa.DateTime, nullable=False),  # Added end_time as DateTime
        sa.Column('p1_customer_affected', sa.Boolean(), nullable=False),
        sa.Column('suspected_affected_components', postgresql.ARRAY(sa.String), nullable=False),
        sa.Column('description', sa.String(250), nullable=False),  # Increased description length
        sa.Column('message_for_sp', sa.String(250), nullable=True),  # Increased message length
        sa.Column('statuspage_notification', sa.Boolean(), nullable=False),  # Changed to match the model
        sa.Column('separate_channel_creation', sa.Boolean(), nullable=False),  # Added separate_channel_creation
        sa.Column('status', sa.String(50), nullable=True),  # Added status
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )


def downgrade() -> None:
    op.drop_table("service_incidents")
