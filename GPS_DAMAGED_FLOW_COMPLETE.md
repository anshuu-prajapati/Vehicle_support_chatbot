# GPS Damaged Flow - LLM Driven Conversational Implementation

## Status: ✅ COMPLETE

## Overview
The GPS Damaged Flow has been converted to a fully conversational, LLM-driven flow that removes all numbered options and question labels (Q10, Q11, Q12). The flow now asks only necessary questions and accepts natural language input.

---

## Flow Design

### Customer Says:
- "GPS toot gaya hai"
- "GPS damage hai"
- "GPS kharab hai"
- "Tracker damage ho gaya hai"
- "Device kharab hai"
- "GPS kaam nahi kar raha"

### LLM Classifies:
`GPS_DAMAGED`

---

## Conversation Flow

### Q1: Location (Current Vehicle Location)
**Bot:**
```
Dhanyavaad. 🙏

Humne note kar liya hai ki GPS device damage ho gaya hai.

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

Aap normal language mein bata sakte hain.

Examples:
• Kal subah
• Aaj shaam
• 22 June
• Monday morning
```

**Customer replies naturally:**
- Example: "Kal subah"
- Example: "22 tarik ko"
- Example: "Monday morning"
- Example: "Aaj shaam"

**LLM Processing:**
- Converts natural language to structured date/time internally
- Uses `_parse_natural_datetime()` function
- Accepts: "kal", "kal subah", "aaj shaam", "22 June", "Monday morning", "agle hafte"
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
Agar inspection visit se pehle koi aur jankari share karna chahte hain to bata sakte hain.

(Yeh optional hai.)
```

**Customer may provide:**
- GPS damage details
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

*Issue:* GPS Damaged

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

#### 1. `app/services/flow_handlers/gps_damaged_flow.py`
**Status:** Complete rewrite with LLM-driven implementation

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

6. **`handle_gps_damaged_flow(...)`**
   - Main flow handler
   - Manages sub-steps: LOCATION, VISIT_DATETIME, CONTACT_CONFIRM, ADDITIONAL_INFO
   - Routes through conversation based on sub_step

7. **`_create_gps_damaged_service_request(...)`**
   - Creates service request ticket
   - Enhanced error handling with detailed logging
   - Builds issue with all collected data
   - Calls `create_service_request_ticket()` with correct parameters
   - Marks conversation_complete before clearing state

**Sub-Steps:**
```python
GPS_DAMAGED_LOCATION = "GPS_DAMAGED_LOCATION"
GPS_DAMAGED_VISIT_DATETIME = "GPS_DAMAGED_VISIT_DATETIME"
GPS_DAMAGED_CONTACT_CONFIRM = "GPS_DAMAGED_CONTACT_CONFIRM"
GPS_DAMAGED_ADDITIONAL_INFO = "GPS_DAMAGED_ADDITIONAL_INFO"
```

#### 2. `app/services/service_engineer_flow_service.py`
**Status:** Updated routing for GPS Damaged Flow

**Changes:**
- Updated initial question when user selects option 5 (GPS Damaged)
- OLD: "Vehicle ki current location kya hai? / What is the current vehicle location?"
- NEW: Conversational message acknowledging damage and asking for location
- Routes to `handle_gps_damaged_flow()` for all GPS Damaged steps

**Updated Routing:**
```python
elif issue_type == "GPS_DAMAGED":
    state_manager.set_state(user_phone, ConversationStep.GPS_DAMAGED_LOCATION)
    return (
        "Dhanyavaad. 🙏\n\n"
        "Humne note kar liya hai ki GPS device damage ho gaya hai.\n\n"
        "Kripya vehicle ki current location bata dijiye jahan inspection karwana hai.\n\n"
        "📍 Example: Kirti Nagar, Delhi"
    )
```

---

## Service Request Details

### Ticket Creation Parameters:
- **vehicle_number**: Retrieved from context or database
- **issue_type**: "GPS_DAMAGED"
- **customer_phone**: User's phone number
- **location**: Vehicle location for inspection
- **inspection_date**: Date object (parsed from natural language)
- **inspection_time**: Time object (parsed from natural language)
- **owner_mobile**: Contact number for engineer
- **driver_name**: Additional info (max 100 chars)

### Data Storage Format:
```python
{
    "vehicle_number": "MH01AB1234",
    "issue_type": "GPS_DAMAGED",
    "customer_phone": "+919876543210",
    "location": "Kirti Nagar mein Najafgarh Road ke paas",
    "inspection_date": date(2026, 6, 17),
    "inspection_time": time(10, 0),
    "owner_mobile": "+919876543210",
    "driver_name": "GPS physical damage, front panel"
}
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

## Changes from OLD Flow

| Aspect | OLD | NEW |
|--------|-----|-----|
| Question Labels | Q10, Q11, Q12 | No labels |
| Date Format | Strict DD/MM/YYYY HH:MM | Natural language: "kal subah", "22 June" |
| Contact | Always asks number | Smart confirmation with LLM |
| Language | English/Hindi mixed | Primarily Hindi with conversational tone |
| Options | No options (already good) | Maintained - no options |
| Understanding | Exact format match | LLM semantic understanding |
| Additional Info | Not collected | Optional collection |

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
**Input:** "22 tarik ko visit karna"
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
**Input:** "GPS ka front panel toot gaya hai"
**Expected:** Should include in driver_name field

---

## Key Features

✅ **No Question Labels:** Removed Q10, Q11, Q12 labels
✅ **No Options:** Already clean, maintained
✅ **Natural Language:** Accepts "kal", "subah", "Monday", etc.
✅ **Conversational Tone:** Hindi-first, friendly language
✅ **LLM Understanding:** Semantic understanding of user intent
✅ **Smart Contact Handling:** Understands confirmation naturally
✅ **Enhanced Logging:** Detailed tracking for debugging
✅ **Error Recovery:** Graceful handling with helpful messages
✅ **Hindi/English/Hinglish:** Supports all three languages
✅ **Optional Additional Info:** Collect damage details if user provides

---

## Intent Classification

User can trigger this flow by saying:

### Natural Language Examples:
- "GPS toot gaya hai"
- "GPS damage hai"
- "GPS kharab hai"
- "Tracker damage ho gaya hai"
- "Device kharab hai"
- "GPS kaam nahi kar raha"
- "GPS jal gaya"
- "GPS physical damage hai"

### Numeric Selection:
- "5" → Direct route to GPS Damaged

LLM classifies as: **GPS_DAMAGED**

---

## Comparison with Other Flows

| Feature | Workshop | Accident | Battery | GPS Removed | Vehicle Running | **GPS Damaged** |
|---------|----------|----------|---------|-------------|-----------------|----------------|
| LLM-Driven | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| No Options | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Natural Date | ✅ | ✅ | ✅ | ✅ | ✅ Natural Date+Time | ✅ Natural Date+Time |
| Optional Info | - | - | - | ✅ | ✅ | ✅ |
| Service Request | ❌ | Sometimes | ❌ | ✅ | ✅ | ✅ Always |
| Contact Confirm | - | - | - | ✅ | ✅ | ✅ |
| Case Closure | ✅ | Sometimes | Sometimes | Sometimes | ❌ | ❌ Never |

---

## Important Notes

1. **Do not force date format** - Accept natural language and convert internally
2. **Do not ask for vehicle number** if already available in database
3. **Do not ask for owner name** if already available in database
4. **Registered mobile pre-filled** - Just confirm or provide alternate
5. **Keep conversation short, natural, and human-like**
6. **Additional info is optional** - Only collected if user volunteers
7. **Contact confirmation uses LLM** - Understands various phrasings
8. **Service request always created** - No case closure path in this flow
9. **Enhanced error handling** - Similar to Vehicle Running flow pattern

---

## Completion Checklist

- [x] Remove question labels (Q10, Q11, Q12)
- [x] Implement natural language date/time parsing
- [x] Remove strict date format requirement
- [x] Implement LLM-driven contact confirmation
- [x] Add optional additional info collection
- [x] Update routing in service_engineer_flow_service.py
- [x] Enhanced error handling and logging
- [x] Service request creation with correct parameters
- [x] Conversation state management (conversation_complete marker)
- [x] Success message with all details
- [x] Make messages conversational and Hindi-first
- [x] Remove English translations where not needed

---

## Next Steps

The GPS Damaged Flow is now complete and ready for testing. When testing:

1. Test with various natural language date inputs
2. Test contact confirmation with different phrasings
3. Verify service request creation with detailed logging
4. Check error scenarios (invalid dates, invalid phones)
5. Verify conversation state clears properly after completion
6. Monitor logs for any unexpected behavior
7. Test with Hindi, English, and Hinglish inputs

---

**Last Updated:** June 16, 2026
**Status:** COMPLETE ✅
