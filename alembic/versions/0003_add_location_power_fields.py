"""Add latitude, longitude and power_state to vehicle_status

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to vehicle_statuses table
    op.add_column('vehicle_statuses', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('vehicle_statuses', sa.Column('longitude', sa.Float(), nullable=True))
    op.add_column('vehicle_statuses', sa.Column('power_state', sa.String(length=20), nullable=True))


def downgrade() -> None:
    # Remove the columns if we need to rollback
    op.drop_column('vehicle_statuses', 'power_state')
    op.drop_column('vehicle_statuses', 'longitude')
    op.drop_column('vehicle_statuses', 'latitude')