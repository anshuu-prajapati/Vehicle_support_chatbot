# GPS Damaged Flow - Added Initial Confirmation Question

## Status: ✅ COMPLETE

---

## What Was Added

Added an **initial confirmation question** in the GPS Damaged flow to ask if the user wants to proceed with GPS installation service request immediately.

---

## New Flow Design

### Initial Question (Q1):
```
Dhanyavaad. 🙏

Humne note kar liya hai ki GPS device damage ho gaya hai.

Kya aap abhi GPS installation ke liye service request continue karna chahte hain?

Main aage ki process complete karke service engineer arrange kar sakta hoon.
```

---

## Two Paths Based on Response

### Path A: YES (User wants service now)
```
User: "Haan"
      "Yes" 
      "Karwana hai"
      "Continue karo"

↓

Bot: Bahut achha! 👍
     Main aage ki process complete karke service engineer arrange kar dunga.
     Kripya vehicle ki current location bata dijiye...

↓ Continue with installation flow:
Q2: Location
Q3: Date/Time
Q4: Contact
Q5: Additional Info
→ Service Request Created ✅
```

---

### Path B: NO (User doesn't want service now)
```
User: "Nahi"
      "Nahin"
      "Abhi nahi"
      "Baad mein"

↓

Bot: Theek hai, koi baat nahi.
     Kripya bataiye ki GPS kab tak running ho jayega ya installation complete ho jayega?
     📅 Expected Date
     Example: 20-06-2026

↓

User provides date: "20-06-2026"

↓

Bot: ✅ Dhanyavaad.
     Expected operational date: 📅 20-06-2026
     Jab GPS installation ke liye ready ho, tab aap hume contact kar sakte hain.
     Case Status: Pending GPS Installation
```

---

## Special Feature: User Changed Mind

If user says **NO** initially but then changes their mind when asked for date:

```
Bot: Kripya bataiye ki GPS kab tak running ho jayega?
     📅 Expected Date

User: "nahi service engineer bhej do"
      "engineer chahiye"
      "installation karwana hai"
      "abhi karwana hai"

↓ LLM detects user wants service

Bot: Bahut achha! 👍
     Main abhi service engineer arrange kar dunga.
     Kripya vehicle ki current location bata dijiye...

↓ Routes to installation flow (Location → Date/Time → Contact → Service Request)
```

---

## Technical Implementation

### New Functions Added:

#### 1. `_wants_gps_installation(text: str) -> bool`
- Detects if user wants to proceed with installation
- Quick checks: "haan", "yes", "karwana", "chahte", "continue"
- LLM fallback for complex responses
- Returns: True (wants service) or False (doesn't want)

#### 2. `_user_changed_mind_wants_service(text: str) -> bool`
- Detects if user changed their mind after saying NO
- Quick checks: "engineer", "service", "bhej", "karwana", "chahiye"
- LLM prompt checks if user is requesting service vs providing date
- Returns: True (wants service now) or False (providing date)

#### 3. `_validate_date(date_str: str) -> tuple`
- Validates date in DD-MM-YYYY or DD/MM/YYYY format
- Returns: (parsed_date, None) or (None, error_message)

---

### New Sub-Steps:

```python
GPS_DAMAGED_CONFIRMATION = "GPS_DAMAGED_CONFIRMATION"  # NEW
GPS_DAMAGED_EXPECTED_DATE = "GPS_DAMAGED_EXPECTED_DATE"  # NEW
GPS_DAMAGED_LOCATION = "GPS_DAMAGED_LOCATION"
GPS_DAMAGED_VISIT_DATETIME = "GPS_DAMAGED_VISIT_DATETIME"
GPS_DAMAGED_CONTACT_CONFIRM = "GPS_DAMAGED_CONTACT_CONFIRM"
GPS_DAMAGED_ADDITIONAL_INFO = "GPS_DAMAGED_ADDITIONAL_INFO"
```

---

## Flow Logic

### Updated Initial Routing:

**File:** `app/services/service_engineer_flow_service.py`

```python
elif issue_type == "GPS_DAMAGED":
    state_manager.set_state(user_phone, ConversationStep.GPS_DAMAGED_LOCATION)
    state_manager.update_context(user_phone, {
        "gps_damaged_sub_step": "GPS_DAMAGED_CONFIRMATION"  # Start with confirmation
    })
    return (
        "Dhanyavaad. 🙏\n\n"
        "Humne note kar liya hai ki GPS device damage ho gaya hai.\n\n"
        "Kya aap abhi GPS installation ke liye service request continue karna chahte hain?\n\n"
        "Main aage ki process complete karke service engineer arrange kar sakta hoon."
    )
```

---

### Main Flow Handler Logic:

**File:** `app/services/flow_handlers/gps_damaged_flow.py`

#### Step 1: Initial Confirmation
```python
if gps_sub_step == GPS_DAMAGED_CONFIRMATION:
    if _wants_gps_installation(text_body):
        # YES path → Go to location
        return "Bahut achha! 👍..."
    else:
        # NO path → Ask for expected date
        return "Theek hai, koi baat nahi..."
```

#### Step 2a: Expected Date (NO path)
```python
if gps_sub_step == GPS_DAMAGED_EXPECTED_DATE:
    # Check if user changed mind
    if _user_changed_mind_wants_service(text_body):
        # User wants service now → Go to location
        return "Bahut achha! 👍..."
    
    # Otherwise validate date
    parsed_date, error = _validate_date(text_body)
    # Store and close case
```

#### Step 2b: Location (YES path)
```python
# After location, continue with date/time → contact → additional info → service request
```

---

## LLM Prompts

### Prompt 1: Installation Confirmation
```
Determine if user wants to proceed with GPS installation service request.

User was asked: "Kya aap abhi GPS installation ke liye service request continue karna chahte hain?"

User replied: "{text}"

Examples of YES: "haan", "yes", "karwana hai", "continue karo"
Examples of NO: "nahi", "abhi nahi", "baad mein"

Respond with: YES or NO
```

### Prompt 2: Changed Mind Detection
```
User was asked for expected date when GPS will be running.

User replied: "{text}"

Determine if user is asking for service engineer instead of providing a date.

Examples of WANTS_SERVICE: "nahi service engineer bhej do", "engineer chahiye"
Examples of PROVIDING_DATE: "20-06-2026", "kal tak", "next week"

Respond with: WANTS_SERVICE or PROVIDING_DATE
```

---

## Testing Scenarios

### Scenario 1: Direct YES
```
Bot: Kya aap abhi GPS installation ke liye service request continue karna chahte hain?
User: Haan
Bot: Bahut achha! 👍 [continues to location]
```

### Scenario 2: Direct NO with Date
```
Bot: Kya aap abhi GPS installation ke liye service request continue karna chahte hain?
User: Nahi
Bot: Theek hai, koi baat nahi. Kripya bataiye ki GPS kab tak running ho jayega?
User: 20-06-2026
Bot: ✅ Dhanyavaad. [case closed]
```

### Scenario 3: Changed Mind (Your Issue)
```
Bot: Kya aap abhi GPS installation ke liye service request continue karna chahte hain?
User: Nahi
Bot: Theek hai, koi baat nahi. Kripya bataiye ki GPS kab tak running ho jayega?
User: nahi service engineer bhej do
Bot: Bahut achha! 👍 [continues to location]
✅ FIXED - No longer shows date validation error
```

### Scenario 4: Various "Changed Mind" Phrases
```
Bot: Expected Date?
User: "engineer chahiye" → Routes to service
User: "installation karwana hai" → Routes to service
User: "service bhej do" → Routes to service
User: "abhi karwana hai" → Routes to service
```

---

## Benefits

✅ **Gives user choice** - Not forcing installation service immediately
✅ **Handles changed mind** - User can reconsider even after saying NO
✅ **Natural conversation** - LLM understands various phrasings
✅ **No date errors** - Detects service request vs date input
✅ **Two outcomes** - Either service request OR case closed with expected date

---

## Files Modified

1. **`app/services/flow_handlers/gps_damaged_flow.py`**
   - Added `_wants_gps_installation()` function
   - Added `_user_changed_mind_wants_service()` function
   - Added `_validate_date()` function
   - Added two new sub-steps
   - Updated flow logic to handle both paths

2. **`app/services/service_engineer_flow_service.py`**
   - Updated initial GPS Damaged question
   - Set initial sub-step to CONFIRMATION

---

## Error Prevention

**Before:**
```
User: nahi service engineer bhej do
Bot: ⚠️ Invalid date format ❌
```

**After:**
```
User: nahi service engineer bhej do
Bot: Bahut achha! 👍 [Routes to service] ✅
```

---

**Status:** COMPLETE ✅
**Date:** June 17, 2026
**Ready for Testing**
