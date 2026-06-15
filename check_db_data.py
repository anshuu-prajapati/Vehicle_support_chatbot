"""
Check what data exists in the database for vehicle breakdown alerts
"""
import sqlite3
import json
from datetime import datetime

db_path = 'ai_support.db'

print("\n" + "="*80)
print("DATABASE INSPECTION FOR BREAKDOWN ALERTS API")
print("="*80)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Check Vehicles
print("\n1. VEHICLES TABLE:")
print("-" * 80)
cursor.execute("SELECT * FROM vehicles")
vehicles = cursor.fetchall()
cursor.execute("PRAGMA table_info(vehicles)")
vehicle_columns = [col[1] for col in cursor.fetchall()]
print(f"Columns: {', '.join(vehicle_columns)}")
print(f"Total rows: {len(vehicles)}")
if vehicles:
    for row in vehicles:
        print(f"  {dict(zip(vehicle_columns, row))}")
else:
    print("  ❌ NO VEHICLES FOUND")

# 2. Check Vehicle Statuses
print("\n2. VEHICLE_STATUSES TABLE:")
print("-" * 80)
cursor.execute("PRAGMA table_info(vehicle_statuses)")
status_columns = [col[1] for col in cursor.fetchall()]
print(f"Columns: {', '.join(status_columns)}")
cursor.execute("SELECT * FROM vehicle_statuses")
statuses = cursor.fetchall()
print(f"Total rows: {len(statuses)}")
if statuses:
    for row in statuses:
        print(f"  {dict(zip(status_columns, row))}")
else:
    print("  ❌ NO STATUSES FOUND")

# 3. Check Alerts
print("\n3. ALERTS TABLE:")
print("-" * 80)
cursor.execute("PRAGMA table_info(alerts)")
alert_columns = [col[1] for col in cursor.fetchall()]
print(f"Columns: {', '.join(alert_columns)}")
cursor.execute("SELECT * FROM alerts")
alerts = cursor.fetchall()
print(f"Total rows: {len(alerts)}")
if alerts:
    for row in alerts:
        print(f"  {dict(zip(alert_columns, row))}")
else:
    print("  ❌ NO ALERTS FOUND")

# 4. Check Vehicle Contacts
print("\n4. VEHICLE_CONTACTS TABLE:")
print("-" * 80)
cursor.execute("PRAGMA table_info(vehicle_contacts)")
contact_columns = [col[1] for col in cursor.fetchall()]
print(f"Columns: {', '.join(contact_columns)}")
cursor.execute("SELECT * FROM vehicle_contacts")
contacts = cursor.fetchall()
print(f"Total rows: {len(contacts)}")
if contacts:
    for row in contacts:
        print(f"  {dict(zip(contact_columns, row))}")
else:
    print("  ❌ NO CONTACTS FOUND")

# 5. Check what the API query would find
print("\n5. BROKEN VEHICLES (API QUERY LOGIC):")
print("-" * 80)
print("API looks for vehicles WHERE:")
print("  - vehicle_statuses.mode = 'not working'")
print("  - alerts.status = 'OPEN'")
print("  - alerts.alert_type = 'VEHICLE_OFF_NOT_WORKING'")
print()

cursor.execute("""
    SELECT 
        v.id as vehicle_id,
        v.vehicle_number,
        vs.mode,
        vs.ign_state,
        vs.power_state,
        a.alert_type,
        a.status as alert_status
    FROM vehicles v
    LEFT JOIN vehicle_statuses vs ON v.id = vs.vehicle_id
    LEFT JOIN alerts a ON v.id = a.vehicle_id
""")
results = cursor.fetchall()
print(f"Total vehicles with joins: {len(results)}")
for row in results:
    print(f"  Vehicle: {row[1]}, Mode: {row[2]}, IGN: {row[3]}, Power: {row[4]}, Alert: {row[5]}, Status: {row[6]}")

# Check specifically for broken vehicles matching API criteria
cursor.execute("""
    SELECT 
        v.id,
        v.vehicle_number,
        vs.mode,
        a.alert_type,
        a.status
    FROM vehicles v
    JOIN vehicle_statuses vs ON v.id = vs.vehicle_id
    JOIN alerts a ON v.id = a.vehicle_id
    WHERE vs.mode = 'not working'
    AND a.status = 'OPEN'
    AND a.alert_type = 'VEHICLE_OFF_NOT_WORKING'
""")
broken = cursor.fetchall()
print(f"\n✅ Vehicles matching API criteria: {len(broken)}")
if broken:
    for row in broken:
        print(f"  Vehicle ID: {row[0]}, Number: {row[1]}")
else:
    print("  ❌ NO VEHICLES MATCH THE API CRITERIA")

# 6. Provide fix instructions
print("\n6. REQUIRED DATA FOR API TO WORK:")
print("-" * 80)
print("You need to add:")
print("1. ✅ Vehicle record in 'vehicles' table")
print("2. ✅ Vehicle status in 'vehicle_statuses' with mode='not working'")
print("3. ❌ Alert record in 'alerts' table with:")
print("   - vehicle_id = (your vehicle ID)")
print("   - alert_type = 'VEHICLE_OFF_NOT_WORKING'")
print("   - status = 'OPEN'")
print("4. ✅ Vehicle contact in 'vehicle_contacts' with phone number")

# Generate JSON output
output = {
    "database": "ai_support.db",
    "timestamp": datetime.now().isoformat(),
    "vehicles": [dict(zip(vehicle_columns, v)) for v in vehicles],
    "statuses": [dict(zip(status_columns, s)) for s in statuses],
    "alerts": [dict(zip(alert_columns, a)) for a in alerts],
    "contacts": [dict(zip(contact_columns, c)) for c in contacts],
    "broken_vehicles_count": len(broken),
    "api_will_work": len(broken) > 0
}

print("\n" + "="*80)
print("JSON OUTPUT:")
print("="*80)
print(json.dumps(output, indent=2, default=str))

conn.close()

print("\n" + "="*80)
print(f"API RESULT: {'✅ WILL WORK' if len(broken) > 0 else '❌ WILL NOT WORK - Missing alert records'}")
print("="*80)
