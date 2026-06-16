# Task 26: Vehicle Running Flow - LLM Conversational Update

## ✅ STATUS: COMPLETE

---

## Task Summary

**Objective:** Convert the Vehicle Running But GPS Not Updating Flow from option-based interaction to fully conversational LLM-driven interaction, removing all numbered options and mandatory driver information.

**Result:** Successfully implemented and integrated.

---

## What Was Done

### 1. Created Complete LLM-Driven Flow Handler
**File:** `app/services/flow_handlers/vehicle_running_flow.py`

#### Implemented Functions:

1. **`_parse_natural_datetime(text: str)`**
   - LLM-powered natural language date/time parsing
   - Accepts: "kal subah", "aaj shaam", "22 June", "Monday afternoon"
   - Converts to structured DD-MM-YYYY and HH:MM format
   - Fallback to standard formats if LLM fails
   - Returns: (date, time, None) or (None, None, error_message)

2. **`_wants_same_contact(text: str)`**
   - LLM-powered contact confirmation understanding
   - Quick checks for affirmative keywords
   - Regex check for phone numbers
   - LLM semantic understanding as fallback
   - Returns: True (same) or False (alternate)

3. **`_validate_phone(phone: str)`**
   - Phone number validation (10-15 digits)

4. **`_get_registered_mobile(user_phone: str, db: Session)`**
   - Retrieves registered mobile from database

5. **`_get_vehicle_number_from_db(user_phone: str, db: Session)`**
   - Retrieves vehicle number from database

6. **`handle_vehicle_running_flow(...)`**
   - Main flow handler with sub-step management
   - Routes through: LOCATION → DATETIME → CONTACT → ADDITIONAL_INFO → SERVICE_REQUEST

7. **`_create_vehicle_running_service_request(...)`**
   - Enhanced error handling with detailed logging
   - Creates service request with correct parameters
   - Builds comprehensive issue description
   - Sets conversation_complete marker before clearing state

---

### 2. Updated Routing
**File:** `app/services/service_engineer_flow_service.py`

**Changed:**
```python
# OLD
"Driver ka naam kya hai?\nWhat is the driver's name?"

# NEW
"Dhanyavaad. 🙏\n\n"
"Hum samajh gaye hain ki vehicle chal rahi hai lekin GPS data receive nahi ho raha.\n\n"
"Kripya vehicle ki current location bata dijiye jahan inspection karwana hai.\n\n"
"📍 Example: Kirti Nagar, Delhi"
```

---

## Flow Design

### Conversation Steps:

#### Step 1: Location
```
Bot: Kripya vehicle ki current location bata dijiye jahan inspection karwana hai.
     📍 Example: Kirti Nagar, Delhi

User: Kirti Nagar mein Najafgarh Road ke paas
```

#### Step 2: Date/Time (Natural Language)
```
Bot: Vehicle inspection ke liye kab available rahegi?
     Aap date aur time normal language mein bata sakte hain.
     Examples: Kal subah, Aaj shaam, 22 June, Monday afternoon

User: Kal subah
     → LLM converts: 17-06-2026, 10:00
```

#### Step 3: Contact Confirmation (LLM-Driven)
```
Bot: Humare records ke anusaar registered mobile number:
     📱 9876543210
     Agar isi number par sampark karna hai to "Theek Hai" likhein.

User: Theek Hai
      → LLM understands: Use same number
```

#### Step 4: Additional Info (Optional)
```
Bot: Agar driver ka naam ya koi additional jankari share karna chahte hain...
     (Yeh optional hai.)

User: Driver Ramesh hai, gate 3 ke paas
      → Saved as additional info
```

#### Step 5: Service Request Created
```
Bot: ✅ Dhanyavaad.
     Aapki service request safalta purvak create kar di gayi hai.
     
     *Issue:* Vehicle Running But GPS Not Updating
     📍 *Location:* Kirti Nagar mein Najafgarh Road ke paas
     📅 *Visit Schedule:* 17-06-2026 at 10:00
     📱 *Contact:* 9876543210
     
     Ticket Number: TKT-1234
```

---

## Key Changes from OLD Flow

| Aspect | OLD | NEW |
|--------|-----|-----|
| Driver Name | Mandatory | Optional (only if user provides) |
| Driver Mobile | Mandatory | Not asked at all |
| Date Format | Strict DD-MM-YYYY HH:MM | Natural language: "kal subah", "22 June" |
| Contact | Always asked separately | Smart confirmation with LLM |
| Options | 1️⃣ Yes, 2️⃣ No buttons | No numbered options |
| Understanding | Exact keyword match | LLM semantic understanding |

---

## Technical Details

### Sub-Steps:
```python
VR_LOCATION = "VR_LOCATION"
VR_VISIT_DATETIME = "VR_VISIT_DATETIME"
VR_CONTACT_CONFIRM = "VR_CONTACT_CONFIRM"
VR_ADDITIONAL_INFO = "VR_ADDITIONAL_INFO"
```

### Service Request Parameters:
- **vehicle_number**: From context or database
- **issue_type**: "VEHICLE_RUNNING_NO_GPS"
- **customer_phone**: User's phone
- **issue_description**: Formatted details
- **priority**: "HIGH"

### Enhanced Error Handling:
- Detailed logging at each step
- Try-catch wrapper for ticket creation
- Context tracking logged
- Vehicle number retrieval logged
- Error messages include debugging info
- Conversation_complete marker set

---

## Intent Classification

User can trigger this flow by:

### Numeric Selection:
- "6" → Direct route to Vehicle Running

### Natural Language:
- "Gaadi chal rahi hai"
- "Vehicle running hai"
- "Driver gaadi chala raha hai"
- "Vehicle operational hai"
- "GPS update nahi ho raha"
- "Tracking nahi aa rahi"

LLM classifies as: **VEHICLE_RUNNING_NO_GPS**

---

## Validation Rules

1. **Location:** Minimum 5 characters
2. **Date:** Must be today or future
3. **Phone:** 10-15 digits (if alternate number)
4. **Natural Date/Time:** LLM parses or fallback to standard formats

---

## Error Messages

| Error | Message |
|-------|---------|
| Location too short | ⚠️ Kripya pura address dein. |
| Past date | ⚠️ Purani date nahi select kar sakte. Kripya aaj ya future ki date dein. |
| Invalid date | ⚠️ Kripya date aur time clear format mein dein (Example: kal subah, 22 June) |
| Invalid phone | ⚠️ Kripya valid mobile number dein. Example: 9876543210 |
| Service creation failed | ⚠️ Service request create karne mein error aaya. Error: {truncated_error} |

---

## Testing Recommendations

### Test Cases:

1. **Natural Date Input:**
   - "Kal" → Should convert to tomorrow
   - "Kal subah" → Should convert to tomorrow 10:00
   - "Aaj shaam" → Should convert to today 18:00
   - "22 June" → Should convert to 22/06/2026 10:00
   - "Monday afternoon" → Should convert to next Monday 14:00

2. **Contact Confirmation:**
   - "Theek Hai" → Should use registered number
   - "Same number" → Should use registered number
   - "Isi number par" → Should use registered number
   - "9876543210" → Should validate and use alternate

3. **Additional Info:**
   - "Nahi" → Should skip and create request
   - "Driver Ramesh" → Should include in description
   - Long text → Should include in description

4. **Error Scenarios:**
   - Past date → Should reject with message
   - Very short location → Should ask for full address
   - Invalid phone format → Should ask for valid number

---

## Files Created/Modified

### Created:
- `VEHICLE_RUNNING_FLOW_COMPLETE.md` - Full documentation
- `VEHICLE_RUNNING_FLOW_SUMMARY.md` - Quick reference
- `TASK_26_VEHICLE_RUNNING_COMPLETE.md` - This file

### Modified:
- `app/services/flow_handlers/vehicle_running_flow.py` - Complete rewrite
- `app/services/service_engineer_flow_service.py` - Updated routing

---

## Comparison with Other Flows

This flow follows the same LLM-driven pattern as:
- ✅ Workshop Flow (Task 18)
- ✅ Accident Flow (Task 20)
- ✅ Battery Flow (Task 21)
- ✅ GPS Removed Flow (Task 22)

**Vehicle Running is now consistent with all other conversational flows.**

---

## Status Checklist

- [x] Remove all numbered options
- [x] Implement natural language date/time parsing
- [x] Remove mandatory driver name question
- [x] Remove mandatory driver mobile question
- [x] Implement LLM-driven contact confirmation
- [x] Add optional additional info collection
- [x] Update routing in service_engineer_flow_service.py
- [x] Enhanced error handling and logging
- [x] Service request creation with correct parameters
- [x] State management with conversation_complete marker
- [x] Success message with all details
- [x] No syntax errors (verified with getDiagnostics)
- [x] Documentation created

---

## Ready for Testing ✅

The Vehicle Running Flow is now fully implemented, tested for syntax errors, and ready for end-to-end testing with real user interactions.

---

**Completed:** June 16, 2026
**Status:** COMPLETE ✅
**Next:** Testing with live environment
