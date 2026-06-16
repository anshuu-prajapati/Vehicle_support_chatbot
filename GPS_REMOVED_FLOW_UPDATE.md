# GPS Removed Flow Update

## Summary
Updated the GPS Removed Flow to follow the new specification with comprehensive natural language support.

## Flow Structure

### When Customer Selects: 4️⃣ GPS Removed

**Q1: Preferred Installation Date**
```
Dhanyavaad. 🙏

GPS ko dobara install kab karwana hai?

📅 Preferred Installation Date

(Example: 20-06-2026)
```
- Accepts: DD-MM-YYYY or DD/MM/YYYY format
- Validates: Must be today or future date

---

**Q2: Current Vehicle Location**
```
Vehicle ki current location kya hai?

📍 Current Vehicle Location

Kripya pura address dein.
```
- Accepts: Free text (minimum 5 characters)
- Example: "Shop No. 5, Main Road, Mumbai - 400001"

---

**Q3: Contact Number Confirmation**
```
Humare records ke anusaar aapka registered mobile number hai:

📱 {registered_mobile_number}

Kya isi number par service engineer sampark kare?

1️⃣ Haan, isi number par
2️⃣ Nahi, doosra number dena hai
```

**Natural Language Support:**
- Option 1: "1", "haan", "isi number par", "yes this number", etc.
- Option 2: "2", "nahi", "dusra number", "doosra number dena hai", etc.

**If Option 1 selected:**
- Uses registered mobile number
- Proceeds to Q4

**If Option 2 selected:**
- Shows: "Kripya alternative mobile number share karein."
- User provides alternate number
- Validates phone number format
- Proceeds to Q4

---

**Q4: Vehicle Availability Date**
```
✅ Dhanyavaad.

Vehicle GPS installation ke liye kab available hogi?

📅 Expected Availability Date

(Example: 22-06-2026)
```
- Accepts: DD-MM-YYYY or DD/MM/YYYY format
- Validates: Must be today or future date

---

**Q5: Additional Information**
```
Dhanyavaad. 🙏

Hum GPS re-installation ke liye nearest service engineer assign karne ja rahe hain.

Kya aap humein koi additional information dena chahte hain?

1️⃣ Yes
2️⃣ No
```

**Natural Language Support:**
- Option 1: "1", "yes", "haan", "haan kuch information deni hai", etc.
- Option 2: "2", "no", "nahi", etc.

**If Option 1 selected:**
- Shows: "Kripya apni additional information share karein."
- User provides notes (free text)
- Saves notes and creates service request

**If Option 2 selected:**
- Creates service request immediately without notes

---

### Final Action

**Service Request Creation:**
1. Create Service Request with issue type: "GPS_REINSTALLATION"
2. Include all collected data:
   - Preferred Installation Date
   - Vehicle Location
   - Contact Number
   - Vehicle Available Date
   - Additional Notes (if provided)
3. Generate ticket number
4. Assign to Nearest Service Engineer (via ticket system)
5. Clear conversation state

**Final Confirmation Message:**
```
✅ Dhanyavaad.

Aapki GPS Reinstallation Service Request safalta purvak create kar di gayi hai.

*Issue Type:* GPS Reinstallation

Hamare nearest service engineer jald hi aapse sampark karenge.

📅 *Preferred Installation Date:* {installation_date}
📍 *Location:* {vehicle_location}
📱 *Contact Number:* {contact_number}
📝 *Additional Notes:* {notes} (if provided)

🙏 Thank You

*Service Request Status:* Created
*Ticket Number:* {ticket_number}
```

---

## Natural Language Support

The flow now accepts **BOTH numeric and natural language responses** at every Yes/No question:

### Q3: Contact Confirmation
- **Numeric:** "1" or "2"
- **Natural Language:** "haan isi number par", "dusra number dena hai", etc.

### Q5: Additional Information
- **Numeric:** "1" or "2"
- **Natural Language:** "yes kuch batana hai", "nahi kuch nahi", etc.

### Implementation Details:
- `_is_affirmative()` function checks for patterns like:
  - "haan", "yes", "isi number par", "information deni hai"
- `_is_negative()` function checks for patterns like:
  - "nahi", "no", "dusra number", "alternate number"
- If input doesn't match patterns, shows options again with:
  ```
  ⚠️ Kripya niche diye gaye options mein se ek chunen:
  ```

---

## Changes Made

### File: `app/services/flow_handlers/gps_removed_flow.py`

**Updated:**
1. ✅ Removed time input requirement (date only)
2. ✅ Added natural language support for Yes/No questions
3. ✅ Simplified to 5 questions total
4. ✅ Added contact number confirmation with alternate option
5. ✅ Added vehicle availability date question
6. ✅ Added optional additional information step
7. ✅ Created `_create_gps_reinstallation_request()` function
8. ✅ Integrated with existing ticket system
9. ✅ Clear state after completion

### File: `app/services/service_engineer_flow_service.py`

**Updated:**
1. ✅ Changed Q1 message to match new specification
2. ✅ Removed time requirement from initial question

---

## Testing Scenarios

### Scenario 1: Numeric Input
```
User: 4
Bot: [Q1 - Installation date]
User: 20-06-2026
Bot: [Q2 - Location]
User: Shop 5, Mumbai
Bot: [Q3 - Contact confirmation]
User: 1
Bot: [Q4 - Availability]
User: 22-06-2026
Bot: [Q5 - Additional info]
User: 2
Bot: [Final confirmation with ticket]
```

### Scenario 2: Natural Language Input
```
User: GPS nikal gaya hai
Bot: [Q1 - Installation date]
User: 20-06-2026
Bot: [Q2 - Location]
User: Shop 5, Mumbai
Bot: [Q3 - Contact confirmation]
User: haan isi number par
Bot: [Q4 - Availability]
User: 22-06-2026
Bot: [Q5 - Additional info]
User: haan kuch batana hai
Bot: [Request for notes]
User: Please come after 2 PM
Bot: [Final confirmation with ticket and notes]
```

### Scenario 3: Alternate Number
```
User: 4
Bot: [Q1 - Installation date]
User: 20/06/2026
Bot: [Q2 - Location]
User: Shop 5, Mumbai
Bot: [Q3 - Contact confirmation]
User: dusra number dena hai
Bot: [Request alternate number]
User: 9876543210
Bot: [Q4 - Availability]
User: 22-06-2026
Bot: [Q5 - Additional info]
User: no
Bot: [Final confirmation with ticket]
```

---

## Error Handling

1. **Invalid Date Format:**
   - Shows: "⚠️ Invalid date format. Please use DD-MM-YYYY or DD/MM/YYYY"

2. **Past Date:**
   - Shows: "⚠️ Purani date nahi select kar sakte"

3. **Invalid Phone Number:**
   - Shows: "⚠️ Kripya sahi mobile number dein"

4. **Invalid Yes/No Response:**
   - Shows: "⚠️ Kripya niche diye gaye options mein se ek chunen"

5. **Service Request Creation Error:**
   - Shows error message
   - Clears state to allow fresh start

---

## Integration Points

### Ticket System
- Uses `create_service_request_ticket()` from `ticket_service.py`
- Issue type: "GPS_REINSTALLATION"
- Priority: "MEDIUM"
- Includes all collected data in description

### State Management
- Uses sub-steps within `GPS_REMOVED_REINSTALL_DATE` step
- Stores progress in context
- Clears state after completion or error

### User Data
- Retrieves registered mobile from User model
- Falls back to user's WhatsApp number if not found

---

## Files Modified

1. ✅ `app/services/flow_handlers/gps_removed_flow.py` - Complete rewrite
2. ✅ `app/services/service_engineer_flow_service.py` - Updated Q1 message

## Files NOT Modified (as per requirements)

- ❌ Database schema
- ❌ Ticket creation logic (used existing)
- ❌ Engineer assignment logic
- ❌ Other flow handlers
- ❌ APIs
- ❌ State management core
- ❌ WhatsApp integration

---

## Status: ✅ COMPLETE

The GPS Removed Flow has been successfully updated to:
1. Follow the exact 5-question flow specified
2. Support both numeric and natural language input
3. Handle contact number confirmation with alternate option
4. Collect optional additional information
5. Create proper service requests with ticket numbers
6. Provide clear confirmation messages
7. Handle all error cases gracefully
