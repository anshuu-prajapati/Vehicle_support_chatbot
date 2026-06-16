# GPS Removed Flow - Final Implementation

## Summary
Updated the GPS Removed Flow with an initial maintenance confirmation question that routes to either case closure or reinstallation flow.

---

## Complete Flow Structure

### Entry Point: Customer Selects 4️⃣ GPS Removed

**Q1: Maintenance/Repair Confirmation**
```
Kya GPS device maintenance ya repair ke liye remove kiya gaya hai?

1️⃣ Yes
2️⃣ No
```

**Natural Language Support for Q1:**
- **YES (Maintenance)**: "1", "yes", "haan", "maintenance ke liye", "service ke liye", "repair ke liye", "testing ke liye", "nikala hai", "remove kiya hai"
- **NO (Not Maintenance)**: "2", "no", "nahi", "chori ho gaya", "stolen", "dobara lagwana hai", "reinstall karna hai", "remove ho gaya"

---

## Path 1: YES - Maintenance/Repair (Case Closure)

### Q2: Expected Operational Date
```
Dhanyavaad. 🙏

Vehicle ya GPS system dobara kab operational hoga?

📅 Expected Running Date

(Example: 20-06-2026)
```

**User provides date**: 20-06-2026

### Final Message (Case Closed)
```
✅ Dhanyavaad.

Humne note kar liya hai ki GPS device maintenance ke liye remove kiya gaya hai.

Expected operational date: 📅 20-06-2026

Is wajah se GPS inactive hona expected hai aur is samay kisi service engineer ki avashyakta nahi hai.

Agar GPS dobara operational hone ke baad bhi issue rahta hai, to aap support request raise kar sakte hain.

🙏 Thank You

Case Status: Closed
```

**Flow Complete** - No service request created, case closed.

---

## Path 2: NO - Not Maintenance (GPS Reinstallation Flow)

### Q3: Preferred Installation Date
```
GPS ko dobara install kab karwana hai?

📅 Preferred Installation Date

(Example: 20-06-2026)
```

### Q4: Current Vehicle Location
```
Vehicle ki current location kya hai?

📍 Current Vehicle Location

Kripya pura address dein.
```

### Q5: Contact Number Confirmation
```
Humare records ke anusaar aapka registered mobile number hai:

📱 {registered_mobile_number}

Kya isi number par service engineer sampark kare?

1️⃣ Haan, isi number par
2️⃣ Nahi, doosra number dena hai
```

**Natural Language Support:**
- Option 1: "1", "haan", "isi number par", "yes this number"
- Option 2: "2", "nahi", "dusra number", "doosra number dena hai", "alternate number"

**If Option 2 selected:**
```
Kripya alternative mobile number share karein.

📱 Alternate Mobile Number

Example: +919876543210 or 9876543210
```

### Q6: Vehicle Availability Date
```
Vehicle GPS installation ke liye kab available hogi?

📅 Expected Availability Date

(Example: 22-06-2026)
```

### Q7: Additional Information
```
Hum GPS re-installation ke liye nearest service engineer assign karne ja rahe hain.

Kya aap humein koi additional information dena chahte hain?

1️⃣ Yes
2️⃣ No
```

**Natural Language Support:**
- Option 1: "1", "yes", "haan", "haan kuch information deni hai"
- Option 2: "2", "no", "nahi"

**If Option 1 selected:**
```
Kripya apni additional information share karein.

📝 Additional Notes
```

### Final Message (Service Request Created)
```
✅ Dhanyavaad.

Aapki GPS Reinstallation Service Request safalta purvak create kar di gayi hai.

Hamare nearest service engineer jald hi aapse sampark karenge.

🙏 Thank You

*Service Request Status:* Created
*Ticket Number:* SR-12345
```

**Flow Complete** - Service request created with ticket number.

---

## Natural Language Examples

### Q1 Examples:

**Maintenance (YES):**
- User: "maintenance ke liye nikala hai"
- User: "service ke liye remove kiya hai"
- User: "testing ke liye nikala tha"
- User: "repair ke liye nikala hai"
- User: "1"
→ Bot routes to Q2 (Expected date) → Case Closed

**Not Maintenance (NO):**
- User: "chori ho gaya"
- User: "remove ho gaya tha"
- User: "dobara lagwana hai"
- User: "reinstall karna hai"
- User: "nikal gaya hai"
- User: "2"
→ Bot routes to Q3 (Reinstallation flow) → Service Request

---

## Key Features

### 1. Smart Pattern Matching
- `_is_affirmative()` checks for maintenance-related keywords
- `_is_negative()` checks for theft/reinstallation keywords
- Accepts both numeric (1/2) and conversational responses

### 2. Two Distinct Paths
- **Maintenance Path**: Quick closure with expected date
- **Reinstallation Path**: Full service request with 7 questions total

### 3. Date Validation
- Accepts DD-MM-YYYY or DD/MM/YYYY formats
- Rejects past dates
- Validates format correctness

### 4. Phone Number Handling
- Retrieves registered number from database
- Offers alternate number option
- Validates phone format (10-15 digits)

### 5. Optional Notes
- User can add additional information
- Notes included in service request description
- Skippable with "No" option

---

## Error Handling

### Invalid Yes/No Response
```
⚠️ Kripya valid option select karein.

Kya GPS device maintenance ya repair ke liye remove kiya gaya hai?

1️⃣ Yes
2️⃣ No
```

### Invalid Date Format
```
⚠️ Invalid date format. Please use DD-MM-YYYY or DD/MM/YYYY (Example: 20-06-2026)
```

### Past Date
```
⚠️ Purani date nahi select kar sakte.
Kripya aaj ya future ki date dein.

Example: 20-06-2026
```

### Invalid Phone Number
```
⚠️ Kripya sahi mobile number dein.

Example: +919876543210 or 9876543210
```

### Service Request Error
```
⚠️ Service request create karne mein error aaya.
⚠️ Error creating service request.

Kripya support team se sampark karein.
Please contact support team.
```

---

## Technical Implementation

### Sub-Steps (stored in context)
- `GPS_REMOVED_EXPECTED_DATE` - Q2 (maintenance path)
- `GPS_REMOVED_INSTALLATION_DATE` - Q3 (reinstallation path)
- `GPS_REMOVED_LOCATION` - Q4
- `GPS_REMOVED_CONTACT_CONFIRM` - Q5
- `GPS_REMOVED_ALTERNATE_NUMBER` - Q5b
- `GPS_REMOVED_AVAILABILITY_DATE` - Q6
- `GPS_REMOVED_ADDITIONAL_INFO` - Q7
- `GPS_REMOVED_ADDITIONAL_NOTES` - Q7b

### Pattern Matching Logic
```python
def _is_affirmative(text: str) -> bool:
    """
    Checks for:
    - Numeric: "1"
    - Keywords: "maintenance", "repair", "service", "testing"
    - Phrases: "maintenance ke liye", "nikala hai"
    """

def _is_negative(text: str) -> bool:
    """
    Checks for:
    - Numeric: "2"
    - Keywords: "chori", "stolen", "reinstall"
    - Phrases: "dobara lagwana", "remove ho gaya"
    - Excludes: maintenance/repair keywords (takes precedence)
    """
```

### Service Request Creation
```python
issue_description = f"GPS Reinstallation Request\n"
issue_description += f"Preferred Installation Date: {installation_date}\n"
issue_description += f"Vehicle Location: {vehicle_location}\n"
issue_description += f"Contact Number: {contact_number}\n"
issue_description += f"Vehicle Available Date: {availability_date}"

if additional_notes:
    issue_description += f"\n\nAdditional Information:\n{additional_notes}"

ticket = create_service_request_ticket(
    user_phone=user_phone,
    issue_type="GPS_REINSTALLATION",
    issue_description=issue_description,
    priority="MEDIUM",
    db=db
)
```

---

## Testing Scenarios

### Scenario 1: Maintenance Case (Case Closure)
```
User: 4
Bot: Kya GPS device maintenance ya repair ke liye remove kiya gaya hai?
User: maintenance ke liye nikala hai
Bot: Vehicle ya GPS system dobara kab operational hoga?
User: 25-06-2026
Bot: ✅ Dhanyavaad... Case Status: Closed
```

### Scenario 2: Reinstallation with Numeric Input
```
User: 4
Bot: Kya GPS device maintenance ya repair ke liye remove kiya gaya hai?
User: 2
Bot: GPS ko dobara install kab karwana hai?
User: 20-06-2026
Bot: Vehicle ki current location kya hai?
User: Shop 5, Mumbai
Bot: Kya isi number par service engineer sampark kare?
User: 1
Bot: Vehicle GPS installation ke liye kab available hogi?
User: 22-06-2026
Bot: Kya aap humein koi additional information dena chahte hain?
User: 2
Bot: ✅ Service Request Created... Ticket Number: SR-12345
```

### Scenario 3: Reinstallation with Natural Language
```
User: GPS nikal gaya hai
Bot: Kya GPS device maintenance ya repair ke liye remove kiya gaya hai?
User: chori ho gaya
Bot: GPS ko dobara install kab karwana hai?
User: 20-06-2026
Bot: Vehicle ki current location kya hai?
User: Shop 5, Mumbai
Bot: Kya isi number par service engineer sampark kare?
User: dusra number dena hai
Bot: Kripya alternative mobile number share karein.
User: 9876543210
Bot: Vehicle GPS installation ke liye kab available hogi?
User: 22-06-2026
Bot: Kya aap humein koi additional information dena chahte hain?
User: haan kuch batana hai
Bot: Kripya apni additional information share karein.
User: Please call after 3 PM
Bot: ✅ Service Request Created... Ticket Number: SR-12345
```

---

## Files Modified

### 1. `app/services/flow_handlers/gps_removed_flow.py`
**Changes:**
- ✅ Added Q1: Maintenance confirmation
- ✅ YES path → Q2: Expected date → Case closure
- ✅ NO path → Q3-Q7: Reinstallation flow → Service request
- ✅ Enhanced natural language support for Q1
- ✅ Simplified final message (removed detailed info)
- ✅ Two distinct flow paths based on Q1 response

### 2. `app/services/service_engineer_flow_service.py`
**Changes:**
- ✅ Updated GPS_REMOVED routing to show Q1 first
- ✅ Changed initial message from installation date to maintenance confirmation

---

## Files NOT Modified

- ❌ Other flow handlers (workshop, accident, battery, etc.)
- ❌ Database schema
- ❌ Ticket creation logic (used existing)
- ❌ Engineer assignment logic
- ❌ APIs
- ❌ State management core
- ❌ WhatsApp integration

---

## Status: ✅ COMPLETE

The GPS Removed Flow now:
1. ✅ Starts with maintenance confirmation (Q1)
2. ✅ Routes to case closure if maintenance (YES path)
3. ✅ Routes to reinstallation flow if not maintenance (NO path)
4. ✅ Accepts natural language responses at Q1
5. ✅ Supports conversational replies throughout
6. ✅ Creates proper service requests with tickets
7. ✅ Handles all error cases gracefully
8. ✅ Provides clear confirmation messages for both paths
