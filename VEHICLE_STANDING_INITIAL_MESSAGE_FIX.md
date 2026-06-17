# Vehicle Standing Flow - Initial Message Fix

## Issue Identified
When user selected option 7 (Vehicle Standing), the bot was sending the OLD message:
```
"Kya aap bata sakte hain vehicle lagbhag kab tak dobara chalne lagegi?"
(When will vehicle start running again?)
```

This was asking for the EXPECTED DATE instead of asking for STANDING DURATION.

## Root Cause
The initial message was defined in `service_engineer_flow_service.py` and was not updated when we redesigned the Vehicle Standing Flow.

## Fix Applied
Updated the initial message in `app/services/service_engineer_flow_service.py` (line 197-208)

### Old Message:
```python
"Kya aap bata sakte hain vehicle lagbhag kab tak dobara chalne lagegi?\n\n"
"📅 Example:\n"
"• Kal\n"
"• 2 din baad\n"
"• Agle hafte\n"
"• 25 June\n"
"• Pata nahi"
```

### New Message:
```python
"Kya aap bata sakte hain vehicle kab se standing condition mein hai?\n\n"
"📅 Examples:\n"
"• Aaj se\n"
"• Kal se\n"
"• 1 din se\n"
"• 2 din se\n"
"• 3 din se\n"
"• Ek hafte se"
```

## Expected Flow Now

### User Journey:
1. **User selects:** 7 (Vehicle Standing)

2. **Bot asks:** "Kya aap bata sakte hain vehicle kab se standing condition mein hai?"
   - Examples: Aaj se, Kal se, 1 din se, 2 din se, etc.

3. **User responds:** "2 din se" (or any duration)

4. **Bot calculates:** 48 hours

5. **Two paths:**
   - **< 48 hours:** Service request flow (Location → Date/Time → Contact → Create ticket)
   - **>= 48 hours:** Expected date → Close case (No service request)

## Files Modified
- `app/services/service_engineer_flow_service.py` - Updated initial VEHICLE_STANDING message

## Status: ✅ FIXED

The Vehicle Standing Flow now correctly asks for standing duration first, then proceeds with the 48-hour threshold logic.
