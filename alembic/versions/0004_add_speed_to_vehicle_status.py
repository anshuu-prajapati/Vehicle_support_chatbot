"""Add speed column to vehicle_statuses table

Revision ID: 0004
Revises: 0003
Create Date: 2024-06-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add speed column to vehicle_statuses table"""
    # Add speed column (Float, nullable)
    op.add_column('vehicle_statuses', sa.Column('speed', sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove speed column from vehicle_statuses table"""
    op.drop_column('vehicle_statuses', 'speed')