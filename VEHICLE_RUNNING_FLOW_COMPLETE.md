# Vehicle Running Flow - LLM Driven Conversational Implementation

## Status: ✅ COMPLETE

## Overview
The Vehicle Running But GPS Not Updating Flow has been converted to a fully conversational, LLM-driven flow that removes all numbered options and mandatory driver information. The flow now asks only necessary questions and accepts natural language input.

---

## Flow Design

### Customer Says:
- "Gaadi chal rahi hai"
- "Vehicle running hai"
- "Driver gaadi chala raha hai"
- "Vehicle operational hai"
- "GPS update nahi ho raha"
- "Tracking nahi aa rahi"

### LLM Classifies:
`VEHICLE_RUNNING_NO_GPS`

---

## Conversation Flow

### Q1: Location (Current Vehicle Location)
**Bot:**
```
Dhanyavaad. 🙏

Hum samajh gaye hain ki vehicle chal rahi hai lekin GPS data receive nahi ho raha.

Kripya vehicle ki current location bata dijiye jahan inspection karwana hai.

📍 Example: Kirti Nagar, Delhi
```

**Customer provides location:**
- Example: "Kirti Nagar mein Najafgarh Road ke paas"
- Example: "Andheri East, Mumbai"

**Validation:**
- Minimum 5 characters required

---

### Q2: Visit Date/Time (Natural Language Accepted)
**Bot:**
```
Dhanyavaad. 📍

Vehicle inspection ke liye kab available rahegi?

Aap date aur time normal language mein bata sakte hain.

Examples:
• Kal subah
• Aaj shaam
• 22 June
• Monday afternoon
• 22 June 10 baje
```

**Customer replies naturally:**
- Example: "Kal subah"
- Example: "22 June"
- Example: "Monday morning"
- Example: "Aaj shaam"

**LLM Processing:**
- Converts natural language to structured date/time internally
- Uses `_parse_natural_datetime()` function
- Accepts: "kal", "kal subah", "aaj shaam", "22 June", "Monday afternoon", "agle hafte"
- Converts internally to DD-MM-YYYY and HH:MM format

**Validation:**
- Date must be today or future
- Invalid format → Error message asking to clarify

---

### Q3: Contact Confirmation (LLM-Driven)
**Bot:**
```
Humare records ke anusaar registered mobile number:

📱 {registered_mobile_number}

Agar isi number par sampark karna hai to "Theek Hai" likhein.
Agar koi doosra number use karna hai to woh number bhej dijiye.
```

**Customer may reply:**
- "Theek Hai"
- "Same number"
- "Isi number par sampark karein"
- OR provide alternate number: "9876543210"

**LLM Processing:**
- Uses `_wants_same_contact()` function
- Quick check for affirmative patterns
- Checks if it looks like a phone number (regex)
- Uses LLM for understanding: "SAME" or "DIFFERENT"

**Validation:**
- If alternate number provided → Validate phone format (10-15 digits)

---

### Q4: Additional Information (Optional)
**Bot:**
```
Agar driver ka naam ya koi additional jankari share karna chahte hain to bata sakte hain.

(Yeh optional hai.)
```

**Customer may provide:**
- Driver Name
- Landmark
- Special Instructions
- OR: "Nahi"

**Processing:**
- If "nahi"/"na"/"no" → Store as None
- If text length > 3 characters → Store as additional_info
- Otherwise → Store as None

---

### Service Request Created

**Bot Response:**
```
✅ Dhanyavaad.

Aapki service request safalta purvak create kar di gayi hai.

*Issue:* Vehicle Running But GPS Not Updating

📍 *Location:* {location}
📅 *Visit Schedule:* {visit_date} at {visit_time}
📱 *Contact:* {contact_number}

Hamare nearest service engineer jald hi aapse sampark karenge.

🙏 Thank You

Service Request Status: Created
Ticket Number: {ticket_number}
```

---

## Technical Implementation

### Files Modified

#### 1. `app/services/flow_handlers/vehicle_running_flow.py`
**Status:** Created/Updated with full LLM-driven implementation

**Key Functions:**

1. **`_parse_natural_datetime(text: str) -> tuple`**
   - Uses LLM to convert natural language date/time to structured format
   - Examples: "kal subah" → (2026-06-17, 10:00)
   - Returns: (parsed_date, parsed_time, None) or (None, None, error_message)
   - Fallback to standard formats if LLM fails

2. **`_wants_same_contact(text: str) -> bool`**
   - LLM-driven understanding of contact confirmation
   - Quick check for affirmative patterns
   - Regex check for phone numbers
   - LLM prompt for natural language understanding
   - Returns: True if wants same contact, False if alternate

3. **`_validate_phone(phone: str) -> bool`**
   - Validates phone number (10-15 digits)

4. **`_get_registered_mobile(user_phone: str, db: Session) -> str`**
   - Retrieves registered mobile from database
   - Fallback to user_phone if not found

5. **`_get_vehicle_number_from_db(user_phone: str, db: Session) -> str`**
   - Retrieves vehicle number associated with user
   - Checks manager_id, supervisor_id, driver_id

6. **`handle_vehicle_running_flow(...)`**
   - Main flow handler
   - Manages sub-steps: VR_LOCATION, VR_VISIT_DATETIME, VR_CONTACT_CONFIRM, VR_ADDITIONAL_INFO
   - Routes through conversation based on sub_step

7. **`_create_vehicle_running_service_request(...)`**
   - Creates service request ticket
   - Enhanced error handling with detailed logging
   - Builds issue description with all collected data
   - Calls `create_service_request_ticket()` with correct parameters
   - Marks conversation_complete before clearing state

**Sub-Steps:**
```python
VR_LOCATION = "VR_LOCATION"
VR_VISIT_DATETIME = "VR_VISIT_DATETIME"
VR_CONTACT_CONFIRM = "VR_CONTACT_CONFIRM"
VR_ADDITIONAL_INFO = "VR_ADDITIONAL_INFO"
```

#### 2. `app/services/service_engineer_flow_service.py`
**Status:** Updated routing for Vehicle Running Flow

**Changes:**
- Updated initial question when user selects option 6 (Vehicle Running)
- OLD: "Driver ka naam kya hai? / What is the driver's name?"
- NEW: Conversational message explaining the issue and asking for location
- Routes to `handle_vehicle_running_flow()` for all Vehicle Running steps

**Updated Routing:**
```python
elif issue_type == "VEHICLE_RUNNING":
    state_manager.set_state(user_phone, ConversationStep.VEHICLE_RUNNING_DRIVER_NAME)
    return (
        "Dhanyavaad. 🙏\n\n"
        "Hum samajh gaye hain ki vehicle chal rahi hai lekin GPS data receive nahi ho raha.\n\n"
        "Kripya vehicle ki current location bata dijiye jahan inspection karwana hai.\n\n"
        "📍 Example: Kirti Nagar, Delhi"
    )
```

---

## Service Request Details

### Ticket Creation Parameters:
- **vehicle_number**: Retrieved from context or database
- **issue_type**: "VEHICLE_RUNNING_NO_GPS"
- **customer_phone**: User's phone number
- **issue_description**: Formatted with all collected information
- **priority**: "HIGH"

### Issue Description Format:
```
Vehicle Running But GPS Not Updating
Inspection Location: {location}
Visit Date: {visit_date}
Visit Time: {visit_time}
Contact Number: {contact_number}

Additional Information:
{additional_info if provided}
```

---

## LLM Integration Patterns

### Pattern 1: Natural Date/Time Parsing
**Function:** `_parse_natural_datetime()`

**LLM Prompt:**
```
Convert this natural language date/time into structured format.

Today's date: {today} ({day_name})

User said: "{text}"

Examples:
- "kal subah" → Tomorrow 10:00 AM
- "aaj shaam" → Today 06:00 PM
- "22 June" → 22/06/2026 10:00 AM

Respond in EXACTLY this format:
DATE: DD/MM/YYYY
TIME: HH:MM
```

**Fallback:** Standard datetime parsing for DD/MM/YYYY HH:MM format

---

### Pattern 2: Contact Confirmation Understanding
**Function:** `_wants_same_contact()`

**LLM Prompt:**
```
Determine if user wants to use the same registered contact number or provide a different one.

User was told: "Agar isi number par sampark karna hai to 'Theek Hai' likhein. 
                Agar koi doosra number use karna hai to woh number bhej dijiye."

User replied: "{text}"

Examples of SAME:
- "theek hai"
- "same number"
- "isi number par sampark karein"

Examples of DIFFERENT:
- "9876543210"
- User provides a phone number

Respond with: SAME or DIFFERENT
```

**Quick Checks:**
1. Affirmative keywords: "theek hai", "same", "isi number", "ok", "haan"
2. Phone number pattern: regex match for 10+ digits
3. LLM understanding (fallback)

---

## Error Handling

### Enhanced Logging:
- Sub-step tracking at each stage
- Context gathering details logged
- Vehicle number retrieval logged
- Ticket creation wrapped in try-catch
- Detailed error messages with phone, error_type, error_message

### Error Scenarios:

1. **Invalid Location:**
   - Check: Minimum 5 characters
   - Message: "⚠️ Kripya pura address dein."

2. **Invalid Date/Time:**
   - LLM cannot parse → Error with example
   - Date in past → "⚠️ Purani date nahi select kar sakte. Kripya aaj ya future ki date dein."

3. **Invalid Phone Number:**
   - Regex validation fails
   - Message: "⚠️ Kripya valid mobile number dein.\n\nExample: 9876543210 or +919876543210"

4. **Service Request Creation Failed:**
   - Wrapped in try-catch with detailed logging
   - Clear state before returning error
   - Message includes truncated error for debugging
   - Conversation_complete marker set before clearing

---

## Testing Scenarios

### Scenario 1: Natural Language Date/Time
**Input:** "Kal subah inspection karwa lo"
**Expected:** Should parse to tomorrow morning (10:00 AM)

### Scenario 2: Specific Date
**Input:** "22 June ko visit karna"
**Expected:** Should parse to 22/06/2026 10:00 AM

### Scenario 3: Same Contact Number
**Input:** "Theek hai, isi number par"
**Expected:** Should use registered number

### Scenario 4: Alternate Contact
**Input:** "9876543210"
**Expected:** Should validate and use alternate number

### Scenario 5: No Additional Info
**Input:** "Nahi"
**Expected:** Should proceed to service request creation without additional notes

### Scenario 6: With Additional Info
**Input:** "Driver ka naam Ramesh hai, gate number 3 ke paas milega"
**Expected:** Should include in issue description

---

## Key Features

✅ **No Numbered Options:** Completely removed 1️⃣, 2️⃣ style options
✅ **Natural Language:** Accepts "kal", "subah", "Monday", etc.
✅ **Optional Driver Info:** No mandatory driver name/mobile questions
✅ **LLM Understanding:** Semantic understanding of user intent
✅ **Smart Contact Handling:** Understands confirmation naturally
✅ **Enhanced Logging:** Detailed tracking for debugging
✅ **Error Recovery:** Graceful handling with helpful messages
✅ **Hindi/English/Hinglish:** Supports all three languages

---

## Important Notes

1. **Do not force date format** - Accept natural language and convert internally
2. **Do not ask for vehicle number** if already available in database
3. **Do not ask for owner details** if already available in database
4. **Keep conversation short, natural, and human-like**
5. **Driver name is optional** - Only collected if user volunteers
6. **Contact confirmation uses LLM** - Understands various phrasings
7. **Service request always created** - No case closure path in this flow
8. **Enhanced error handling** - Similar to GPS Removed flow pattern

---

## Comparison with Other Flows

| Feature | Workshop | Accident | Battery | GPS Removed | **Vehicle Running** |
|---------|----------|----------|---------|-------------|-------------------|
| LLM-Driven | ✅ | ✅ | ✅ | ✅ | ✅ |
| No Options | ✅ | ✅ | ✅ | ✅ | ✅ |
| Natural Date | ✅ | ✅ | ✅ | ✅ | ✅ Natural Date+Time |
| Optional Info | - | - | - | ✅ | ✅ |
| Service Request | ❌ | Sometimes | ❌ | ✅ | ✅ Always |
| Contact Confirm | - | - | - | ✅ | ✅ |
| Case Closure | ✅ | Sometimes | Sometimes | Sometimes | ❌ Never |

---

## Completion Checklist

- [x] Remove numbered options from all questions
- [x] Implement natural language date/time parsing
- [x] Remove mandatory driver name question
- [x] Remove mandatory driver mobile question
- [x] Implement LLM-driven contact confirmation
- [x] Add optional additional info collection
- [x] Update routing in service_engineer_flow_service.py
- [x] Enhanced error handling and logging
- [x] Service request creation with correct parameters
- [x] Conversation state management (conversation_complete marker)
- [x] Success message with all details

---

## Next Steps

The Vehicle Running Flow is now complete and ready for testing. When testing:

1. Test with various natural language date inputs
2. Test contact confirmation with different phrasings
3. Verify service request creation with detailed logging
4. Check error scenarios (invalid dates, invalid phones)
5. Verify conversation state clears properly after completion
6. Monitor logs for any unexpected behavior

---

**Last Updated:** June 16, 2026
**Status:** COMPLETE ✅
