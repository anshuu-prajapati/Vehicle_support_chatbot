# Vehicle Status Update API Documentation

This document describes the new API endpoints for updating and retrieving vehicle status information including GPS coordinates, power state, and ignition state.

## 📋 Overview

The Vehicle Status API provides two main endpoints:
1. **PUT /vehicles/status/update** - Update vehicle status fields
2. **GET /vehicles/status/{vehicle_number}** - Get current vehicle status

## 🔧 API Endpoints

### 1. Update Vehicle Status

**Endpoint**: `PUT /vehicles/status/update`

**Description**: Update one or more status fields for a vehicle in a single API call.

#### Request Body

```json
{
  "vehicle_number": "string (required)",
  "latitude": "float (optional)",
  "longitude": "float (optional)", 
  "power_state": "string (optional)",
  "ignition_state": "string (optional)"
}
```

#### Field Validation

| Field | Type | Validation | Example |
|-------|------|------------|---------|
| `vehicle_number` | string | Required, normalized to uppercase | "DL01AB1234" |
| `latitude` | float | Optional, must be -90 to 90 | 28.6139 |
| `longitude` | float | Optional, must be -180 to 180 | 77.2090 |
| `power_state` | string | Optional, must be: "on", "off", "unknown" | "on" |
| `ignition_state` | string | Optional, must be: "on", "off", "unknown" | "on" |

#### Example Request

```bash
curl -X PUT "http://127.0.0.1:8000/vehicles/status/update" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_number": "TEST-100",
    "latitude": 28.6139,
    "longitude": 77.2090,
    "power_state": "on",
    "ignition_state": "on"
  }'
```

#### Response

```json
{
  "success": true,
  "message": "Successfully updated 4 field(s) for vehicle TEST-100",
  "vehicle_number": "TEST-100",
  "updated_fields": {
    "latitude": {
      "old_value": null,
      "new_value": 28.6139
    },
    "longitude": {
      "old_value": null,
      "new_value": 77.2090
    },
    "power_state": {
      "old_value": null,
      "new_value": "on"
    },
    "ignition_state": {
      "old_value": "off",
      "new_value": "on"
    },
    "last_gps_time": {
      "old_value": null,
      "new_value": "2026-06-05T12:00:00.000Z"
    },
    "location": {
      "old_value": "Test Depot",
      "new_value": "GPS: 28.6139, 77.2090"
    }
  },
  "timestamp": "2026-06-05T12:00:00.000Z"
}
```

### 2. Get Vehicle Status

**Endpoint**: `GET /vehicles/status/{vehicle_number}`

**Description**: Retrieve current vehicle status information from the database.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `vehicle_number` | string | Vehicle registration number |

#### Example Request

```bash
curl -X GET "http://127.0.0.1:8000/vehicles/status/TEST-100" \
  -H "Content-Type: application/json"
```

#### Response

```json
{
  "vehicle_number": "TEST-100",
  "company_name": "Tech Solutions Pvt Ltd",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "power_state": "on",
  "ignition_state": "on",
  "mode": "not working",
  "location": "GPS: 28.6139, 77.2090",
  "last_gps_time": "2026-06-05T12:00:00.000Z",
  "not_working_hours": 0
}
```

## 🎯 Usage Examples

### Update All Fields

```json
{
  "vehicle_number": "DL01AB1234",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "power_state": "on",
  "ignition_state": "on"
}
```

### Update Only GPS Coordinates

```json
{
  "vehicle_number": "DL01AB1234",
  "latitude": 28.7041,
  "longitude": 77.1025
}
```

### Update Only Power and Ignition States

```json
{
  "vehicle_number": "DL01AB1234",
  "power_state": "off",
  "ignition_state": "off"
}
```

### Turn Off Vehicle

```json
{
  "vehicle_number": "DL01AB1234",
  "power_state": "off",
  "ignition_state": "off"
}
```

## 🔍 Database Impact

### Automatic Updates

When location data is provided, the API automatically:
1. **Updates GPS timestamp** - Sets `last_gps_time` to current UTC time
2. **Updates location text** - Sets `location` to "GPS: lat, lng" format
3. **Tracks changes** - Returns old and new values for all updated fields

### Database Schema

The API updates the `vehicle_statuses` table:

```sql
CREATE TABLE vehicle_statuses (
    id INTEGER PRIMARY KEY,
    vehicle_id INTEGER NOT NULL,
    ign_state VARCHAR(20),           -- Updated by ignition_state
    mode VARCHAR(50),
    location VARCHAR(255),           -- Auto-updated when GPS provided
    latitude FLOAT,                  -- Updated by latitude
    longitude FLOAT,                 -- Updated by longitude  
    power_state VARCHAR(20),         -- Updated by power_state
    last_gps_time TIMESTAMP,         -- Auto-updated when GPS provided
    not_working_hours INTEGER DEFAULT 0
);
```

## ⚠️ Error Handling

### Validation Errors (400)

```json
{
  "detail": [
    {
      "loc": ["body", "latitude"],
      "msg": "Latitude must be between -90 and 90",
      "type": "value_error"
    }
  ]
}
```

### Vehicle Not Found (404)

```json
{
  "success": false,
  "message": "Vehicle 'INVALID123' not found in database",
  "vehicle_number": "INVALID123",
  "updated_fields": {},
  "timestamp": "2026-06-05T12:00:00.000Z"
}
```

### Server Error (500)

```json
{
  "detail": "Failed to update vehicle status: Database connection error"
}
```

## 🚀 Integration with GPS Repair Flow

The updated fields can be used in the GPS repair conversation flow:

### Check GPS Coordinates
```python
if vehicle_status.latitude and vehicle_status.longitude:
    print(f"GPS location: {vehicle_status.latitude}, {vehicle_status.longitude}")
else:
    print("GPS coordinates not available")
```

### Verify Power and Ignition States
```python
if vehicle_status.power_state == "off":
    print("Vehicle power is off - this may affect GPS")

if vehicle_status.ign_state == "on" and vehicle_status.power_state == "on":
    print("Vehicle is powered and ignition is on")
```

## 📊 Logging and Monitoring

The API provides comprehensive logging:
- **Request logging** - All API calls are logged with parameters
- **Field tracking** - Changes to each field are logged with old/new values
- **Error logging** - Validation errors and database issues are logged
- **Performance monitoring** - Response times and success rates

## 🔒 Security Considerations

- **Input validation** - All fields are validated before database updates
- **SQL injection protection** - Uses SQLAlchemy ORM with parameterized queries
- **Rate limiting** - Consider adding rate limiting for production use
- **Authentication** - Consider adding API key authentication for production

## 📈 Future Enhancements

Potential future improvements:
1. **Batch updates** - Update multiple vehicles in one API call
2. **Historical tracking** - Store history of status changes
3. **Real-time notifications** - WebSocket updates when status changes
4. **Geofencing** - Alerts when vehicles enter/exit specific areas
5. **Status validation** - Cross-validate GPS data with ignition state

## 🧪 Testing

Use the provided test script:

```bash
python test_vehicle_status_api.py
```

The test script demonstrates:
- Updating all fields
- Partial updates
- Validation error handling
- Status retrieval after updates

---

**Note**: This API is designed to work with the existing GPS repair flow and vehicle alert system. Updates to vehicle status will be reflected in the troubleshooting conversations and breakdown alerts.