"""Extend tickets table for service engineer assignment

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    """Add new columns to tickets table for service engineer assignment workflow"""
    
    # Add issue type classification
    op.add_column('tickets', sa.Column('issue_type', sa.String(50), nullable=True))
    
    # Add vehicle information
    op.add_column('tickets', sa.Column('vehicle_number', sa.String(100), nullable=True))
    
    # Add owner information
    op.add_column('tickets', sa.Column('owner_name', sa.String(100), nullable=True))
    op.add_column('tickets', sa.Column('owner_mobile', sa.String(20), nullable=True))
    
    # Add driver information (different from existing driver_phone)
    op.add_column('tickets', sa.Column('driver_name', sa.String(100), nullable=True))
    op.add_column('tickets', sa.Column('driver_mobile', sa.String(20), nullable=True))
    
    # Add location information
    op.add_column('tickets', sa.Column('location', sa.String(255), nullable=True))
    
    # Add visit scheduling information
    op.add_column('tickets', sa.Column('visit_date', sa.Date(), nullable=True))
    op.add_column('tickets', sa.Column('visit_time', sa.Time(), nullable=True))
    
    # Add GPS reinstallation scheduling
    op.add_column('tickets', sa.Column('reinstallation_date', sa.Date(), nullable=True))
    op.add_column('tickets', sa.Column('reinstallation_time', sa.Time(), nullable=True))
    
    # Add vehicle availability information
    op.add_column('tickets', sa.Column('vehicle_available', sa.Boolean(), nullable=True))
    op.add_column('tickets', sa.Column('vehicle_available_date', sa.Date(), nullable=True))
    op.add_column('tickets', sa.Column('vehicle_available_time', sa.Time(), nullable=True))
    
    # Add inspection scheduling
    op.add_column('tickets', sa.Column('inspection_date', sa.Date(), nullable=True))
    op.add_column('tickets', sa.Column('inspection_time', sa.Time(), nullable=True))
    
    # Add vehicle standing duration
    op.add_column('tickets', sa.Column('standing_duration', sa.String(50), nullable=True))
    
    # Add closure reason for auto-closed tickets
    op.add_column('tickets', sa.Column('closure_reason', sa.String(100), nullable=True))
    
    # Add assigned engineer (SQLite doesn't support adding FK constraints, will be handled at application level)
    op.add_column('tickets', sa.Column('assigned_engineer_id', sa.Integer(), nullable=True))
    
    # Add indexes for faster lookups
    op.create_index('ix_tickets_vehicle_number', 'tickets', ['vehicle_number'])
    op.create_index('ix_tickets_issue_type', 'tickets', ['issue_type'])
    op.create_index('ix_tickets_status', 'tickets', ['status'])


def downgrade():
    """Remove all added columns and constraints"""
    
    # Drop indexes
    op.drop_index('ix_tickets_status', 'tickets')
    op.drop_index('ix_tickets_issue_type', 'tickets')
    op.drop_index('ix_tickets_vehicle_number', 'tickets')
    
    # Drop all added columns
    op.drop_column('tickets', 'assigned_engineer_id')
    op.drop_column('tickets', 'closure_reason')
    op.drop_column('tickets', 'standing_duration')
    op.drop_column('tickets', 'inspection_time')
    op.drop_column('tickets', 'inspection_date')
    op.drop_column('tickets', 'vehicle_available_time')
    op.drop_column('tickets', 'vehicle_available_date')
    op.drop_column('tickets', 'vehicle_available')
    op.drop_column('tickets', 'reinstallation_time')
    op.drop_column('tickets', 'reinstallation_date')
    op.drop_column('tickets', 'visit_time')
    op.drop_column('tickets', 'visit_date')
    op.drop_column('tickets', 'location')
    op.drop_column('tickets', 'driver_mobile')
    op.drop_column('tickets', 'driver_name')
    op.drop_column('tickets', 'owner_mobile')
    op.drop_column('tickets', 'owner_name')
    op.drop_column('tickets', 'vehicle_number')
    op.drop_column('tickets', 'issue_type')
