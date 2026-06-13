#!/usr/bin/env python3
"""
Database migration script to add latitude, longitude and power_state fields
to vehicle_statuses table.

Usage:
    python run_migration.py

This script will:
1. Check if the new fields exist in the database
2. Add them if they don't exist  
3. Update existing records with default values for power_state
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from app.db.database import run_schema_migrations, engine
    from sqlalchemy import text, inspect
    
    def add_vehicle_status_fields():
        """Add new fields to vehicle_statuses table"""
        
        print("🔍 Checking database schema...")
        
        inspector = inspect(engine)
        
        # Check if vehicle_statuses table exists
        if "vehicle_statuses" not in inspector.get_table_names():
            print("❌ vehicle_statuses table not found!")
            return False
            
        # Get current columns
        current_columns = [col["name"] for col in inspector.get_columns("vehicle_statuses")]
        print(f"📋 Current columns: {', '.join(current_columns)}")
        
        # Fields to add
        fields_to_add = {
            "latitude": "FLOAT",
            "longitude": "FLOAT", 
            "power_state": "VARCHAR(20)"
        }
        
        added_fields = []
        
        with engine.begin() as connection:
            for field_name, field_type in fields_to_add.items():
                if field_name not in current_columns:
                    print(f"➕ Adding {field_name} column...")
                    connection.execute(text(f"ALTER TABLE vehicle_statuses ADD COLUMN {field_name} {field_type}"))
                    added_fields.append(field_name)
                else:
                    print(f"✅ {field_name} column already exists")
            
            # Update power_state with default values if it was just added
            if "power_state" in added_fields:
                print("🔄 Updating existing records with default power state values...")
                result = connection.execute(text("""
                    UPDATE vehicle_statuses 
                    SET power_state = CASE 
                        WHEN ign_state = 'on' THEN 'on'
                        WHEN ign_state = 'off' THEN 'off'
                        ELSE 'unknown'
                    END
                    WHERE power_state IS NULL
                """))
                print(f"📊 Updated {result.rowcount} records")
        
        if added_fields:
            print(f"✅ Successfully added fields: {', '.join(added_fields)}")
        else:
            print("✅ All fields already exist - no migration needed")
            
        return True
    
    def verify_migration():
        """Verify that all fields were added correctly"""
        print("\n🔍 Verifying migration...")
        
        with engine.begin() as connection:
            result = connection.execute(text("""
                SELECT 
                    column_name, 
                    data_type, 
                    is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'vehicle_statuses' 
                AND column_name IN ('latitude', 'longitude', 'power_state')
                ORDER BY column_name
            """))
            
            fields = result.fetchall()
            if fields:
                print("📋 New fields in database:")
                for field in fields:
                    print(f"   • {field[0]}: {field[1]} (nullable: {field[2]})")
            else:
                print("❌ No new fields found!")
                return False
                
        return True
    
    if __name__ == "__main__":
        print("🚀 Starting vehicle_statuses migration...")
        print("=" * 50)
        
        try:
            # Run the migration
            success = add_vehicle_status_fields()
            
            if success:
                # Verify the migration worked
                verify_migration()
                print("\n" + "=" * 50)
                print("✅ Migration completed successfully!")
                print("\n📝 New fields available in VehicleStatus model:")
                print("   • latitude (Float) - GPS latitude coordinate")
                print("   • longitude (Float) - GPS longitude coordinate") 
                print("   • power_state (String) - Vehicle power status")
            else:
                print("❌ Migration failed!")
                sys.exit(1)
                
        except Exception as e:
            print(f"❌ Error during migration: {str(e)}")
            sys.exit(1)

except ImportError as e:
    print(f"❌ Missing dependencies: {str(e)}")
    print("💡 Please install requirements: pip install -r requirements.txt")
    sys.exit(1)