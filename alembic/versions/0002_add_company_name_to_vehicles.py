"""Add company_name to vehicles table

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001_create_conversation_states'
branch_labels = None
depends_on = None


def upgrade():
    """Add company_name column to vehicles table"""
    
    # Add company_name column
    op.add_column('vehicles', sa.Column('company_name', sa.String(200), nullable=True))
    
    # Update existing records with dummy company names
    # Using different company names for variety
    op.execute("""
        UPDATE vehicles 
        SET company_name = CASE 
            WHEN id % 4 = 0 THEN 'Tech Solutions Pvt Ltd'
            WHEN id % 4 = 1 THEN 'Global Logistics Corp'
            WHEN id % 4 = 2 THEN 'Swift Transport Services'
            WHEN id % 4 = 3 THEN 'Metro Fleet Management'
            ELSE 'Tech Solutions Pvt Ltd'
        END
        WHERE company_name IS NULL
    """)


def downgrade():
    """Remove company_name column from vehicles table"""
    
    op.drop_column('vehicles', 'company_name')