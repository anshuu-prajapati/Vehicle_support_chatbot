# Vehicle Breakdown Alert API

## Overview
This API provides proactive WhatsApp messaging functionality for broken/not-working vehicles. It automatically detects vehicles that are down and sends alerts to managers and owners.

## New API Endpoints

### 1. Send Breakdown Alerts
**POST** `/vehicles/send-breakdown-alerts`

**Description:** Sends WhatsApp alerts to managers about all currently broken vehicles

**Response:**
```json
{
  "success": true,
  "message": "Alert sent to 2 manager(s) about 1 broken vehicle(s)",
  "vehicles_count": 1,
  "alerts_sent": 2,
  "failed_sends": [],
  "vehicles_data": [
    {
      "vehicle_id": 1,
      "vehicle_number": "TEST-100",
      "location": "Test Depot",
      "last_gps_time": "2026-06-03 01:02:43",
      "alert_created": "2026-06-03 06:12:37",
      "manager_name": "Test Manager",
      "manager_phone": "+919999999999",
      "contacts": [
        {
          "type": "OWNER",
          "owner_phone": "+918882374849",
          "driver_phone": "+918290323758",
          "is_primary": true
        }
      ]
    }
  ]
}
```

### 2. Get Breakdown Status  
**GET** `/vehicles/breakdown-status`

**Description:** Gets current broken vehicles status without sending alerts (for monitoring)

## WhatsApp Message Format

When alerts are sent, managers receive this message:

```
🚨 *VEHICLE ALERT* 🚨

Aapke fleet mein *1* vehicle(s) breakdown/not working hai:

*1. Vehicle TEST-100*
📍 Location: Test Depot
🕐 Last GPS: 2026-06-03 01:02:43
⏰ Alert Time: 2026-06-03 06:12:37
👤 Owner: +918882374849
🚛 Driver: +918290323758

Do you need assistance? Reply with:
1️⃣ YES - Engineer assistance chahiye
2️⃣ NO - We are handling it

Support Team
```

## Database Integration

### Tables Used:
- `vehicles` - Vehicle master data
- `vehicle_statuses` - Current vehicle status (`not working`)
- `alerts` - Active alerts (`OPEN` status, `VEHICLE_OFF_NOT_WORKING` type)
- `users` - Manager/driver contact information
- `vehicle_contacts` - Vehicle-specific contact mappings

### Query Logic:
```sql
SELECT v.*, vs.*, a.*, u.*
FROM vehicles v
JOIN vehicle_statuses vs ON v.id = vs.vehicle_id  
JOIN alerts a ON v.id = a.vehicle_id
LEFT JOIN users u ON v.manager_id = u.id
WHERE vs.mode = 'not working'
  AND a.status = 'OPEN' 
  AND a.alert_type = 'VEHICLE_OFF_NOT_WORKING'
```

## Use Cases

### 1. Automated Monitoring
```bash
# Set up a cron job to check every 30 minutes
curl -X POST http://127.0.0.1:8000/vehicles/send-breakdown-alerts
```

### 2. Manual Dashboard Check
```bash
# Check status without sending alerts
curl -X GET http://127.0.0.1:8000/vehicles/breakdown-status
```

### 3. Integration with Monitoring Systems
```python
import requests

response = requests.post("http://127.0.0.1:8000/vehicles/send-breakdown-alerts")
result = response.json()

if result["vehicles_count"] > 0:
    print(f"Alert: {result['vehicles_count']} vehicles need attention")
```

## Features

### ✅ Implemented
- **Multi-vehicle detection** - Finds all broken vehicles in one call
- **Bilingual messaging** - Hindi/English WhatsApp messages
- **Contact management** - Sends to managers, owners, and primary contacts
- **Rich vehicle data** - Location, GPS time, alert timestamps
- **Error handling** - Tracks failed message sends
- **Duplicate prevention** - Sends one alert per unique phone number

### 🎯 Business Benefits  
- **Proactive support** - No need to wait for customer complaints
- **Faster response** - Immediate alerts when vehicles break down
- **Complete visibility** - All broken vehicles in fleet at once
- **Multi-channel contact** - Reaches managers, owners, and drivers
- **Audit trail** - Tracks when alerts were sent and to whom

## Error Handling

The API handles various error scenarios:
- **No broken vehicles** - Returns success with 0 count
- **WhatsApp delivery failures** - Logs failed sends but continues
- **Database connection issues** - Returns 500 error
- **Missing contact information** - Skips vehicles with no contacts

## Testing with Your Data

Based on your current database, this API will find:
- **Vehicle:** TEST-100  
- **Status:** not working
- **Location:** Test Depot
- **Managers:** +919999999999, +918882374849
- **Alert Type:** VEHICLE_OFF_NOT_WORKING

## Integration Points

This API integrates seamlessly with:
- ✅ **Existing WhatsApp service** (`whatsapp_service.py`)
- ✅ **Database models** (Vehicle, VehicleStatus, Alert, User)
- ✅ **Logging system** (Structured logging)
- ✅ **FastAPI framework** (RESTful endpoints)
- ✅ **Existing vehicle API** (`/vehicles/*` routes)

## Next Steps for Production

1. **Scheduling** - Set up automated calls (cron/task scheduler)
2. **Monitoring** - Add metrics and dashboards  
3. **Escalation** - Auto-escalate if no response after X hours
4. **Filtering** - Add parameters to filter by location, time, etc.
5. **Templates** - Make message templates configurable