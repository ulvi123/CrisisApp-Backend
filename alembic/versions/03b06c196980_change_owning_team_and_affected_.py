"""Change owning_team and affected_products to ARRAY

Revision ID: 03b06c196980
Revises: 603192a121f4
Create Date: 2024-07-16 23:31:39.668151

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '03b06c196980'
down_revision: Union[str, None] = '603192a121f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Manually transform existing data into array literals
    op.execute("UPDATE service_incidents SET affected_products = '{' || affected_products || '}' WHERE affected_products IS NOT NULL")
    op.execute("UPDATE service_incidents SET suspected_owning_team = '{' || suspected_owning_team || '}' WHERE suspected_owning_team IS NOT NULL")
    op.execute("UPDATE service_incidents SET suspected_affected_components = '{' || suspected_affected_components || '}' WHERE suspected_affected_components IS NOT NULL")

    # Change columns to ARRAY type with explicit cast
    op.execute('ALTER TABLE service_incidents ALTER COLUMN affected_products TYPE character varying[] USING affected_products::character varying[]')
    op.execute('ALTER TABLE service_incidents ALTER COLUMN suspected_owning_team TYPE character varying[] USING suspected_owning_team::character varying[]')
    op.execute('ALTER TABLE service_incidents ALTER COLUMN suspected_affected_components TYPE character varying[] USING suspected_affected_components::character varying[]')

def downgrade():
    # Revert columns to String type with explicit cast
    op.execute('ALTER TABLE service_incidents ALTER COLUMN affected_products TYPE character varying USING affected_products::character varying')
    op.execute('ALTER TABLE service_incidents ALTER COLUMN suspected_owning_team TYPE character varying USING suspected_owning_team::character varying')
    op.execute('ALTER TABLE service_incidents ALTER COLUMN suspected_affected_components TYPE character varying USING suspected_affected_components::character varying')