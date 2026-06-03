# AI Support System - CRUD API Documentation

## Base URL
```
http://localhost:8000
```

## API Endpoints Overview

### User Management APIs

#### 1. Create a User
**POST** `/users/`

Create a new user (manager, supervisor, driver, or customer)

**Request Body:**
```json
{
  "name": "Manager Raj",
  "phone_number": "+918882374849",
  "role": "manager"
}
```

**Response (200):**
```json
{
  "id": 1,
  "name": "Manager Raj",
  "phone_number": "+918882374849",
  "role": "manager",
  "created_at": "2026-06-03T12:00:00"
}
```

---

#### 2. Get All Users
**GET** `/users/`

Get all users with optional filtering

**Query Parameters:**
- `role` (optional): Filter by role (manager, supervisor, driver, customer)
- `skip` (optional): Pagination offset (default: 0)
- `limit` (optional): Number of results (default: 100)

**Example:**
```
GET /users/?role=manager&skip=0&limit=10
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Manager Raj",
    "phone_number": "+918882374849",
    "role": "manager"
  },
  {
    "id": 2,
    "name": "Manager Priya",
    "phone_number": "+919988776655",
    "role": "manager"
  }
]
```

---

#### 3. Get User by ID
**GET** `/users/{user_id}`

Get a specific user by ID

**Example:**
```
GET /users/1
```

**Response:**
```json
{
  "id": 1,
  "name": "Manager Raj",
  "phone_number": "+918882374849",
  "role": "manager",
  "created_at": "2026-06-03T12:00:00"
}
```

---

#### 4. Get User by Phone Number
**GET** `/users/phone/{phone_number}`

Get a specific user by phone number

**Example:**
```
GET /users/phone/8882374849
```

**Response:**
```json
{
  "id": 1,
  "name": "Manager Raj",
  "phone_number": "+918882374849",
  "role": "manager",
  "created_at": "2026-06-03T12:00:00"
}
```

---

#### 5. Update User
**PUT** `/users/{user_id}`

Update user details

**Request Body (all fields optional):**
```json
{
  "name": "Manager Raj Updated",
  "phone_number": "+918882374850",
  "role": "supervisor"
}
```

**Response:**
```json
{
  "id": 1,
  "name": "Manager Raj Updated",
  "phone_number": "+918882374850",
  "role": "supervisor",
  "created_at": "2026-06-03T12:00:00"
}
```

---

#### 6. Delete User
**DELETE** `/users/{user_id}`

Delete a user

**Example:**
```
DELETE /users/1
```

**Response:**
```json
{
  "status": "success",
  "message": "User 1 deleted successfully",
  "user_id": 1
}
```

---

#### 7. Get All Managers
**GET** `/users/role/managers/list`

Get all managers

**Query Parameters:**
- `skip` (optional): Pagination offset
- `limit` (optional): Number of results

**Response:**
```json
[
  {
    "id": 1,
    "name": "Manager Raj",
    "phone_number": "+918882374849",
    "role": "manager"
  }
]
```

---

#### 8. Get All Supervisors
**GET** `/users/role/supervisors/list`

Get all supervisors

**Response:**
```json
[
  {
    "id": 3,
    "name": "Supervisor Amit",
    "phone_number": "+919876543210",
    "role": "supervisor"
  }
]
```

---

#### 9. Get All Drivers
**GET** `/users/role/drivers/list`

Get all drivers

**Response:**
```json
[
  {
    "id": 2,
    "name": "Driver Vikram",
    "phone_number": "+919988776655",
    "role": "driver"
  }
]
```

---

### Vehicle Management APIs

#### 1. Create a Vehicle
**POST** `/vehicles/`

Create a new vehicle with optional manager, supervisor, and driver assignments

**Request Body:**
```json
{
  "vehicle_number": "DL-01-AB-1234",
  "manager_id": 1,
  "supervisor_id": 3,
  "driver_id": 2
}
```

**Response (200):**
```json
{
  "id": 1,
  "vehicle_number": "DL-01-AB-1234",
  "manager_id": 1,
  "supervisor_id": 3,
  "driver_id": 2
}
```

---

#### 2. Get All Vehicles
**GET** `/vehicles/`

Get all vehicles

**Query Parameters:**
- `skip` (optional): Pagination offset
- `limit` (optional): Number of results

**Response:**
```json
[
  {
    "id": 1,
    "vehicle_number": "DL-01-AB-1234",
    "manager_id": 1,
    "supervisor_id": 3,
    "driver_id": 2
  }
]
```

---

#### 3. Get Vehicle by ID
**GET** `/vehicles/{vehicle_id}`

Get a specific vehicle with all details

**Example:**
```
GET /vehicles/1
```

**Response:**
```json
{
  "id": 1,
  "vehicle_number": "DL-01-AB-1234",
  "manager_id": 1,
  "supervisor_id": 3,
  "driver_id": 2,
  "manager": {
    "id": 1,
    "name": "Manager Raj",
    "phone_number": "+918882374849"
  },
  "supervisor": {
    "id": 3,
    "name": "Supervisor Amit",
    "phone_number": "+919876543210"
  },
  "driver": {
    "id": 2,
    "name": "Driver Vikram",
    "phone_number": "+919988776655"
  }
}
```

---

#### 4. Get Vehicle by Vehicle Number
**GET** `/vehicles/number/{vehicle_number}`

Get a vehicle by its vehicle number

**Example:**
```
GET /vehicles/number/DL-01-AB-1234
```

**Response:**
```json
{
  "id": 1,
  "vehicle_number": "DL-01-AB-1234",
  "manager_id": 1,
  "supervisor_id": 3,
  "driver_id": 2,
  "manager": {...},
  "supervisor": {...},
  "driver": {...}
}
```

---

#### 5. Update Vehicle
**PUT** `/vehicles/{vehicle_id}`

Update vehicle details or reassign users

**Request Body (all fields optional):**
```json
{
  "vehicle_number": "DL-01-AB-5678",
  "manager_id": 1,
  "supervisor_id": 0,
  "driver_id": 2
}
```

**Note:** Use `0` as value to unassign a user

**Response:**
```json
{
  "id": 1,
  "vehicle_number": "DL-01-AB-5678",
  "manager_id": 1,
  "supervisor_id": null,
  "driver_id": 2
}
```

---

#### 6. Delete Vehicle
**DELETE** `/vehicles/{vehicle_id}`

Delete a vehicle

**Example:**
```
DELETE /vehicles/1
```

**Response:**
```json
{
  "status": "success",
  "message": "Vehicle 1 deleted successfully",
  "vehicle_id": 1,
  "vehicle_number": "DL-01-AB-1234"
}
```

---

#### 7. Create/Update Vehicle Status
**POST** `/vehicles/{vehicle_id}/status`

Create or update vehicle status (GPS, mode, etc.)

**Request Body:**
```json
{
  "ign_state": "off",
  "mode": "not working",
  "location": "Noida Depot",
  "last_gps_time": "2026-06-03T12:00:00",
  "not_working_hours": 2
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Vehicle status updated",
  "vehicle_id": 1,
  "ign_state": "off",
  "mode": "not working",
  "location": "Noida Depot",
  "not_working_hours": 2
}
```

---

#### 8. Get Vehicle Status
**GET** `/vehicles/{vehicle_id}/status`

Get current vehicle status

**Example:**
```
GET /vehicles/1/status
```

**Response:**
```json
{
  "vehicle_id": 1,
  "vehicle_number": "DL-01-AB-1234",
  "ign_state": "off",
  "mode": "not working",
  "location": "Noida Depot",
  "last_gps_time": "2026-06-03T12:00:00",
  "not_working_hours": 2
}
```

---

#### 9. Get All NOT WORKING Vehicles
**GET** `/vehicles/status/not-working/list`

Get all vehicles that are currently NOT WORKING

**Query Parameters:**
- `skip` (optional): Pagination offset
- `limit` (optional): Number of results

**Response:**
```json
[
  {
    "vehicle_id": 1,
    "vehicle_number": "DL-01-AB-1234",
    "ign_state": "off",
    "mode": "not working",
    "location": "Noida Depot",
    "last_gps_time": "2026-06-03T12:00:00",
    "not_working_hours": 2
  }
]
```

---

## Quick Start Examples

### Example 1: Create a complete setup with users and vehicles

**Step 1: Create Manager**
```bash
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Manager Raj",
    "phone_number": "+918882374849",
    "role": "manager"
  }'
```

**Step 2: Create Driver**
```bash
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Driver Amit",
    "phone_number": "+918290323758",
    "role": "driver"
  }'
```

**Step 3: Create Supervisor**
```bash
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Supervisor Vikram",
    "phone_number": "+919876543210",
    "role": "supervisor"
  }'
```

**Step 4: Create Vehicle**
```bash
curl -X POST "http://localhost:8000/vehicles/" \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_number": "DL-01-AB-1234",
    "manager_id": 1,
    "supervisor_id": 3,
    "driver_id": 2
  }'
```

**Step 5: Set Vehicle Status**
```bash
curl -X POST "http://localhost:8000/vehicles/1/status" \
  -H "Content-Type: application/json" \
  -d '{
    "ign_state": "off",
    "mode": "not working",
    "location": "Noida Depot",
    "last_gps_time": "2026-06-03T12:00:00",
    "not_working_hours": 1
  }'
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message here"
}
```

### Common Errors:

| Status Code | Message |
|---|---|
| 400 | User/Vehicle with this identifier already exists |
| 400 | Invalid phone number format |
| 404 | User/Vehicle not found |
| 404 | Manager/Supervisor/Driver not found |
| 500 | Internal server error |

---

## Usage Tips

1. **Phone Numbers**: All phone numbers are automatically normalized to include country code (e.g., +91)
2. **Roles**: Valid roles are `manager`, `supervisor`, `driver`, `customer`
3. **Unassign Users**: To unassign a user from a vehicle, use `0` in the update request
4. **Pagination**: Use `skip` and `limit` for large datasets
5. **Filtering**: Use query parameters to filter results by role, status, etc.

---

## Testing with Postman

Import these endpoints into Postman and test easily:

1. Set base URL: `http://localhost:8000`
2. Create collection: "AI Support System"
3. Add requests for each endpoint
4. Use variables for `{user_id}` and `{vehicle_id}`

---

## Integration with WhatsApp Flow

These APIs feed into the WhatsApp conversation system:
- Users created via API can receive WhatsApp messages
- Vehicles can be monitored and alerts triggered
- Manager/Supervisor/Driver roles determine alert routing
- Status updates trigger the alert system automatically
