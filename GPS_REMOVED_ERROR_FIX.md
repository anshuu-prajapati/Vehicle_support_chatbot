# GPS Removed Flow - Service Request Error Fix

## Error Description
```
⚠️ Service request create karne mein error aaya.
⚠️ Error creating service request.
Kripya support team se sampark karein.
Please contact support team.
```

## Root Cause

The `create_service_request_ticket()` function has the following signature:
```python
def create_service_request_ticket(
    vehicle_number: str,      # REQUIRED
    issue_type: str,          # REQUIRED
    customer_phone: str,      # REQUIRED
    **kwargs
):
```

### Issue in GPS Removed Flow
The GPS Removed Flow was calling it incorrectly:
```python
# INCORRECT CALL
ticket = create_service_request_ticket(
    user_phone=user_phone,              # ❌ Wrong parameter name
    issue_type="GPS_REINSTALLATION",
    issue_description=issue_description,
    priority="MEDIUM",
    db=db                                # ❌ db is not a parameter
)
```

**Problems:**
1. ❌ Missing `vehicle_number` (required parameter)
2. ❌ Using `user_phone` instead of `customer_phone`
3. ❌ Passing `db` as a parameter (not accepted)

---

## Solution

### Fixed Function Call
```python
# CORRECT CALL
ticket = create_service_request_ticket(
    vehicle_number=vehicle_number,      # ✅ Retrieved from context or DB
    issue_type="GPS_REINSTALLATION",    # ✅ Correct
    customer_phone=user_phone,          # ✅ Correct parameter name
    issue_description=issue_description,
    priority="MEDIUM"
)
```

### Added Helper Function
```python
def _get_vehicle_number_from_db(user_phone: str, db: Session) -> str:
    """Get vehicle number associated with user from database"""
    try:
        from app.db.models.user import User
        from app.db.models.vehicle import Vehicle
        
        user = db.query(User).filter(User.phone_number == user_phone).first()
        if not user:
            return None
        
        vehicle = db.query(Vehicle).filter(
            (Vehicle.manager_id == user.id) |
            (Vehicle.supervisor_id == user.id) |
            (Vehicle.driver_id == user.id)
        ).first()
        
        return vehicle.vehicle_number if vehicle else None
    except Exception as e:
        logger.error(f"Error getting vehicle number: {str(e)}")
        return None
```

### Updated Service Request Creation Logic
```python
def _create_gps_reinstallation_request(...):
    try:
        context = state_manager.get_context(user_phone)
        
        # Get vehicle number from context or database
        vehicle_number = context.get("vehicle_number")
        if not vehicle_number:
            vehicle_number = _get_vehicle_number_from_db(user_phone, db)
        
        if not vehicle_number:
            logger.error(f"GPS Removed: No vehicle number found for {user_phone}")
            vehicle_number = "UNKNOWN"  # Fallback to prevent crash
        
        # Create service request ticket with correct parameters
        ticket = create_service_request_ticket(
            vehicle_number=vehicle_number,          # ✅ Required
            issue_type="GPS_REINSTALLATION",        # ✅ Required
            customer_phone=user_phone,              # ✅ Required
            issue_description=issue_description,
            priority="MEDIUM"
        )
        
        # ... rest of the code
```

---

## Why This Error Occurred

### Function Signature Mismatch
The `create_service_request_ticket()` function expects **positional arguments**:
1. `vehicle_number` (position 0)
2. `issue_type` (position 1)
3. `customer_phone` (position 2)

When we called it with `user_phone=...` instead of `customer_phone=...`, Python couldn't match the parameter and raised an error.

### Missing Vehicle Number
The GPS Removed Flow collects:
- Installation date
- Location
- Contact number
- Availability date
- Additional notes

But it **never collected the vehicle number**, which is required by the ticket system.

---

## How It Works Now

### Vehicle Number Resolution
1. **Try Context First**: Check if `vehicle_number` is already in context (may have been set by webhook/alert)
2. **Query Database**: If not in context, query the database using user's phone number
3. **Fallback**: If still not found, use "UNKNOWN" to prevent crash (with error log)

### Database Query
The helper function queries:
```sql
SELECT vehicle_number FROM vehicles
WHERE manager_id = {user_id}
   OR supervisor_id = {user_id}
   OR driver_id = {user_id}
LIMIT 1
```

This finds the vehicle associated with the user in any role (manager, supervisor, or driver).

---

## Testing

### Test Scenario 1: Vehicle in Context
```python
context = {
    "vehicle_number": "MH12AB1234",  # Already set by webhook
    "gps_removed_installation_date": "20-06-2026",
    # ... other fields
}
# Result: Uses "MH12AB1234" directly
```

### Test Scenario 2: Vehicle from Database
```python
context = {
    # No vehicle_number in context
    "gps_removed_installation_date": "20-06-2026",
    # ... other fields
}
# Result: Queries DB, finds "MH12AB1234", uses it
```

### Test Scenario 3: No Vehicle Found
```python
context = {
    # No vehicle_number in context
    "gps_removed_installation_date": "20-06-2026",
    # ... other fields
}
# User not in database or no vehicle associated
# Result: Uses "UNKNOWN", logs error, but doesn't crash
```

---

## Files Modified

### `app/services/flow_handlers/gps_removed_flow.py`

**Added:**
1. ✅ `_get_vehicle_number_from_db()` helper function
2. ✅ Vehicle number resolution logic in `_create_gps_reinstallation_request()`
3. ✅ Fixed function call parameters to `create_service_request_ticket()`

**Changes:**
```python
# BEFORE
ticket = create_service_request_ticket(
    user_phone=user_phone,
    issue_type="GPS_REINSTALLATION",
    issue_description=issue_description,
    priority="MEDIUM",
    db=db
)

# AFTER
vehicle_number = context.get("vehicle_number")
if not vehicle_number:
    vehicle_number = _get_vehicle_number_from_db(user_phone, db)

if not vehicle_number:
    vehicle_number = "UNKNOWN"

ticket = create_service_request_ticket(
    vehicle_number=vehicle_number,
    issue_type="GPS_REINSTALLATION",
    customer_phone=user_phone,
    issue_description=issue_description,
    priority="MEDIUM"
)
```

---

## Expected Behavior After Fix

### Successful Service Request Creation
```
✅ Dhanyavaad.

Aapki GPS Reinstallation Service Request safalta purvak create kar di gayi hai.

Hamare nearest service engineer jald hi aapse sampark karenge.

🙏 Thank You

*Service Request Status:* Created
*Ticket Number:* TKT-1001
```

### Database Entry
```sql
INSERT INTO tickets (
    ticket_number,
    vehicle_number,        -- Now properly filled
    customer_phone,        -- Now properly filled
    issue_type,
    problem,
    status,
    created_at
) VALUES (
    'TKT-1001',
    'MH12AB1234',          -- From context or DB
    '+919876543210',       -- User's phone
    'GPS_REINSTALLATION',
    'GPS Reinstallation Request\n...',
    'OPEN',
    NOW()
);
```

---

## Prevention for Other Flows

### Checklist for Creating Service Requests
When calling `create_service_request_ticket()`, always ensure:

1. ✅ `vehicle_number` is available (from context or DB)
2. ✅ Use `customer_phone` not `user_phone`
3. ✅ Don't pass `db` as a parameter (function creates its own session)
4. ✅ Use correct parameter names

### Example Template
```python
# Get vehicle number
vehicle_number = context.get("vehicle_number")
if not vehicle_number:
    vehicle_number = _get_vehicle_number_from_db(user_phone, db)

if not vehicle_number:
    logger.error(f"No vehicle found for {user_phone}")
    # Handle error gracefully

# Create ticket
ticket = create_service_request_ticket(
    vehicle_number=vehicle_number,       # Required
    issue_type="YOUR_ISSUE_TYPE",        # Required
    customer_phone=user_phone,           # Required
    issue_description="...",             # Optional
    priority="MEDIUM"                    # Optional
)
```

---

## Status: ✅ FIXED

The GPS Removed Flow service request creation error has been resolved by:
1. ✅ Adding vehicle number resolution from context or database
2. ✅ Fixing parameter names in function call
3. ✅ Removing invalid `db` parameter
4. ✅ Adding proper error logging
5. ✅ Implementing graceful fallback to "UNKNOWN" if no vehicle found
