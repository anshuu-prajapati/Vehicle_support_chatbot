"""
Verification script for migration 0005 - Service Engineer Assignment fields
"""
import sqlite3
from datetime import datetime

def verify_migration():
    """Verify that all new columns exist in the tickets table"""
    
    conn = sqlite3.connect('ai_support.db')
    cursor = conn.cursor()
    
    # Get table schema
    cursor.execute('PRAGMA table_info(tickets)')
    columns = {row[1]: row[2] for row in cursor.fetchall()}
    
    # Expected new columns from migration 0005
    expected_columns = {
        'issue_type': 'VARCHAR(50)',
        'vehicle_number': 'VARCHAR(100)',
        'owner_name': 'VARCHAR(100)',
        'owner_mobile': 'VARCHAR(20)',
        'driver_name': 'VARCHAR(100)',
        'driver_mobile': 'VARCHAR(20)',
        'location': 'VARCHAR(255)',
        'visit_date': 'DATE',
        'visit_time': 'TIME',
        'reinstallation_date': 'DATE',
        'reinstallation_time': 'TIME',
        'vehicle_available': 'BOOLEAN',
        'vehicle_available_date': 'DATE',
        'vehicle_available_time': 'TIME',
        'inspection_date': 'DATE',
        'inspection_time': 'TIME',
        'standing_duration': 'VARCHAR(50)',
        'closure_reason': 'VARCHAR(100)',
        'assigned_engineer_id': 'INTEGER'
    }
    
    print("=" * 80)
    print("MIGRATION 0005 VERIFICATION")
    print("=" * 80)
    print()
    
    # Check each expected column
    missing_columns = []
    present_columns = []
    
    for col_name, col_type in expected_columns.items():
        if col_name in columns:
            present_columns.append(col_name)
            print(f"✓ {col_name:<30} ({columns[col_name]})")
        else:
            missing_columns.append(col_name)
            print(f"✗ {col_name:<30} MISSING!")
    
    print()
    print("=" * 80)
    print(f"SUMMARY: {len(present_columns)}/{len(expected_columns)} columns present")
    print("=" * 80)
    
    if missing_columns:
        print(f"\n❌ MIGRATION INCOMPLETE - Missing columns: {', '.join(missing_columns)}")
        conn.close()
        return False
    else:
        print("\n✅ MIGRATION COMPLETE - All service engineer fields are present!")
    
    # Check indexes
    print("\n" + "=" * 80)
    print("CHECKING INDEXES")
    print("=" * 80)
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='tickets'")
    indexes = [row[0] for row in cursor.fetchall()]
    
    expected_indexes = [
        'ix_tickets_vehicle_number',
        'ix_tickets_issue_type',
        'ix_tickets_status'
    ]
    
    for idx_name in expected_indexes:
        if idx_name in indexes:
            print(f"✓ {idx_name}")
        else:
            print(f"✗ {idx_name} MISSING (will be created on next migration run)")
    
    # Check alembic version
    print("\n" + "=" * 80)
    print("ALEMBIC VERSION")
    print("=" * 80)
    
    cursor.execute("SELECT version_num FROM alembic_version")
    result = cursor.fetchone()
    if result:
        version = result[0]
        print(f"Current version: {version}")
        if version == '0005':
            print("✅ Database is at the latest migration (0005)")
        else:
            print(f"⚠️  Database is at version {version}, expected 0005")
    else:
        print("❌ No alembic version found!")
    
    conn.close()
    return True

if __name__ == "__main__":
    verify_migration()
