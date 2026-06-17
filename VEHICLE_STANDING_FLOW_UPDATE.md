# Vehicle Standing Flow - Updated Implementation

## Date: June 17, 2026

## Summary
Successfully updated the Vehicle Standing Flow to implement 48-hour threshold logic with conversational LLM-driven understanding and global clarification support.

---

## New Flow Logic

### Step 1: Standing Duration Check
**Bot asks:** "Kya aap bata sakte hain vehicle kab se standing condition mein hai?"

**Examples accepted:**
- "aaj se" → 12 hours
- "kal se" → 36 hours  
- "1 din se" → 24 hours
- "2 din se" → 48 hours
- "3 din se" → 72 hours
- "ek hafte se" → 168 hours

**LLM Function:** `_parse_standing_duration()` converts natural language to hours

---

## Two Paths Based on Duration

### Path A: Standing >= 48 Hours (Close Case)

**Step 2:** Ask expected running date
- Bot: "Vehicle ko dobara chalne mein lagbhag kitna samay lag sakta hai?"
- Examples: "Kal", "2 din baad", "Agle hafte", "25 June", "Pata nahi"

**Step 3:** Close case with message:
```
✅ Dhanyavaad.
Humne note kar liya hai ki vehicle 48 ghante se adhik samay se standing condition mein hai.
Expected operational date: 📅 {date}
Is samay kisi service engineer ki avashyakta nahi hai.
🙏 Thank You
Case Status: Closed
```

**Key Points:**
- NO service request created
- Case closed immediately
- Expected date optional (accepts "pata nahi")

---

### Path B: Standing < 48 Hours (Service Request)

**Step 2:** Location
- Bot: "Vehicle ki current location bata dijiye jahan inspection karwana hai."
- Example: "Kirti Nagar, Delhi"

**Step 3:** Visit Date/Time (Natural Language)
- Bot: "Vehicle inspection ke liye kab available rahegi?"
- Examples: "Kal subah", "Aaj shaam", "22 June", "Monday morning"
- LLM Function: `_parse_natural_datetime()`

**Step 4:** Contact Confirmation
- Bot shows registered number
- User: "Theek Hai" (use registered) or provides alternate number
- LLM Function: `_wants_same_contact()`

**Step 5:** Create Service Request
```
✅ Dhanyavaad.
Aapki service request safalta purvak create kar di gayi hai.
Issue: Vehicle Standing - GPS Not Updating
📍 Location: {location}
📅 Visit Schedule: {date} at {time}
📱 Contact: {number}
Service Request Status: Created
Ticket Number: {ticket_number}
```

---

## Technical Implementation

### New Functions Added

1. **`_parse_standing_duration(text: str) -> tuple`**
   - Converts natural language to hours
   - Returns: `(hours, None)` or `(None, error_message)`
   - Examples: "2 din se" → 48 hours

2. **`_parse_natural_datetime(text: str) -> tuple`**
   - Parses date and time from natural language
   - Returns: `(date, time, None)` or `(None, None, error_message)`
   - Examples: "kal subah" → (tomorrow, 10:00)

3. **`_wants_same_contact(text: str) -> bool`**
   - LLM-driven contact confirmation
   - Returns: True if user wants registered number

4. **`_create_vehicle_standing_service_request()`**
   - Creates service request for < 48 hours case
   - Issue type: "VEHICLE_STANDING_GPS_NOT_UPDATING"
   - Stores standing duration in `driver_name` field

### Sub-Steps (Context Keys)

```python
VS_EXPECTED_DATE = "VS_EXPECTED_DATE"      # For >= 48 hours
VS_LOCATION = "VS_LOCATION"                # For < 48 hours
VS_VISIT_DATETIME = "VS_VISIT_DATETIME"    # For < 48 hours
VS_CONTACT_CONFIRM = "VS_CONTACT_CONFIRM"  # For < 48 hours
```

### Context Keys Stored

**Common:**
- `standing_hours`: Duration in hours
- `vs_sub_step`: Current sub-step

**>= 48 Hours Path:**
- `standing_expected_date`: Expected running date
- `standing_status`: "MORE_THAN_48_HOURS" or "MORE_THAN_48_HOURS_NO_DATE"
- `case_status`: "CLOSED"

**< 48 Hours Path:**
- `vs_location`: Inspection location
- `vs_visit_date`: Visit date (DD-MM-YYYY)
- `vs_visit_time`: Visit time (HH:MM)
- `vs_contact_number`: Contact number
- `service_request_id`: Ticket number
- `case_status`: "SERVICE_REQUEST_CREATED"

---

## Global Clarification Support

### Integrated Clarification Handler

At every step, if user says:
- "Mujhe samajh nahi aaya"
- "Kya matlab?"
- "Kyun pooch rahe ho?"
- "Explain karo"

**Bot behavior:**
1. Detects confusion using `should_clarify()`
2. Provides context-specific explanation
3. Re-asks the same question
4. **Does NOT advance workflow**

### Context-Specific Explanations

**Initial Question:**
"Hum pooch rahe hain ki vehicle kab se standing condition mein hai. Isse hum decide kar sakte hain ki service engineer ki zarurat hai ya nahi."

**Expected Date:**
"Hum pooch rahe hain ki vehicle lagbhag kab dobara chalne lagegi. Isse humein samajhne mein madad milti hai ki GPS issue vehicle standing hone ki wajah se hai ya kisi technical issue ki wajah se."

**Location:**
"Hum vehicle ki location isliye pooch rahe hain taaki service engineer ko pata rahe kahan aana hai GPS check karne ke liye."

**Visit Date:**
"Hum pooch rahe hain ki inspection ke liye vehicle kab available rahegi taaki service engineer ki visit schedule kar sakein."

**Contact:**
"Hum confirm kar rahe hain ki kis number par aapse contact karna hai service engineer ke visit ke liye."

---

## Database Fields Used

### Ticket Model Fields (< 48 Hours Path)

```python
ticket = create_service_request_ticket(
    vehicle_number=vehicle_number,
    issue_type="VEHICLE_STANDING_GPS_NOT_UPDATING",
    customer_phone=user_phone,
    location=location,                    # Inspection location
    inspection_date=visit_date_obj,       # Date object
    inspection_time=visit_time_obj,       # Time object
    owner_mobile=contact_number,          # Confirmed contact
    driver_name=standing_info             # "Standing Xhrs"
)
```

---

## Flow Decision Logic

```
Standing Duration
       ↓
   Parse Hours
       ↓
    < 48h? ────NO──→ Ask Expected Date → Close Case
       │
      YES
       ↓
Ask Location → Ask Date/Time → Ask Contact → Create Service Request
```

---

## Key Features

### ✅ Implemented
- [x] LLM-driven standing duration parsing
- [x] 48-hour threshold check
- [x] Two distinct paths based on duration
- [x] Natural language date/time understanding
- [x] LLM contact confirmation
- [x] Service request creation (< 48 hours)
- [x] Case closure (>= 48 hours)
- [x] Global clarification handler at every step
- [x] Detailed logging throughout
- [x] Error handling and validation
- [x] Proper Ticket model field usage

### 🎯 Business Logic
- **< 48 hours:** GPS issue likely technical → Create service request
- **>= 48 hours:** GPS issue likely due to standing → Close case, no service needed

---

## Files Modified

1. **`app/services/flow_handlers/vehicle_standing_flow.py`**
   - Complete rewrite with new logic
   - Added 4 new helper functions
   - Integrated clarification handler
   - Implemented 48-hour threshold

---

## Testing Scenarios

### Scenario 1: Vehicle Standing 1 Day (< 48h)
```
Bot: Vehicle kab se standing condition mein hai?
User: Kal se
Bot: [Asks location]
User: Kirti Nagar, Delhi
Bot: [Asks visit date/time]
User: Kal subah
Bot: [Confirms contact]
User: Theek Hai
Bot: ✅ Service request created
```

### Scenario 2: Vehicle Standing 3 Days (>= 48h)
```
Bot: Vehicle kab se standing condition mein hai?
User: 3 din se
Bot: Vehicle ko dobara chalne mein lagbhag kitna samay lag sakta hai?
User: 2 din baad
Bot: ✅ Case closed - No service needed
```

### Scenario 3: Clarification Request
```
Bot: Vehicle kab se standing condition mein hai?
User: Mujhe samajh nahi aaya
Bot: [Explains why asking + Re-asks question]
User: 2 din se
Bot: [Continues flow normally]
```

---

## No Changes Made To

- ✅ Other flow handlers
- ✅ Routing logic  
- ✅ Database schema
- ✅ API endpoints
- ✅ State management system
- ✅ Ticket creation logic (used existing function)
- ✅ Engineer assignment logic
- ✅ WhatsApp integration

---

## Success Criteria Met

✅ Fully conversational LLM-driven flow
✅ No option buttons or numbered menus
✅ Natural language accepted throughout
✅ 48-hour threshold implemented correctly
✅ Service request for < 48 hours
✅ Case closure for >= 48 hours  
✅ Global clarification support at every step
✅ Proper error handling and logging
✅ Follows existing code patterns

---

## Status: ✅ COMPLETE

The Vehicle Standing Flow is now fully functional with the new 48-hour threshold logic and conversational interface.
