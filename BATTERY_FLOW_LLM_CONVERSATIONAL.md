# Battery Disconnect Flow - LLM-Driven Conversational Update

## Summary
Completely redesigned the Battery Disconnect Flow to use LLM-driven natural language understanding with conversational reclassification instead of menu-based reselection.

---

## Flow Structure

### Entry: User selects "Battery Disconnect" (Option 3)

**From Initial Selection:**
- User: "3" OR "battery nikali hai" OR "battery disconnect hai"
- Bot routes to Battery Disconnect Flow

---

## Complete Conversational Flow

### Q1: Battery Maintenance Confirmation (LLM-Driven)

**Bot asks:**
```
Dhanyavaad. 🙏

Kya battery maintenance, replacement ya repair ke liye disconnect ki gayi hai?
```

**User can respond naturally:**

#### YES Responses (Battery Maintenance):
- "haan"
- "yes"
- "maintenance ke liye nikali hai"
- "battery change ho rahi hai"
- "replacement chal raha hai"
- "repair ke liye disconnect ki hai"
- "battery nikali hui hai maintenance ke liye"
- "battery change kar rahe hain"

#### NO Responses (Not Battery Maintenance):
- "nahi"
- "no"
- "battery nahi nikali"
- "maintenance nahi chal rahi"
- "battery disconnect nahi hai"
- "galti se select ho gaya"
- "wrong option"

---

### Path 1: Battery Maintenance (YES)

**Q2: Expected Date**

**Bot asks:**
```
Vehicle ya battery system dobara kab operational hoga?

Example: 20-06-2026
```

**User provides date:**
```
20-06-2026
```

**Bot confirms (Case Closed):**
```
✅ Dhanyavaad.

Humne note kar liya hai ki battery maintenance/replacement ke kaaran vehicle inactive hai.

Expected availability date: 📅 20-06-2026

Is samay kisi service engineer ki avashyakta nahi hai.

Agar battery reconnect hone ke baad bhi GPS issue rahta hai, to aap support request raise kar sakte hain.

🙏 Thank You

Case Status: Closed
```

---

### Path 2: NOT Battery Maintenance (NO)

**Q3: Describe Situation (Natural Language Reclassification)**

**Bot asks:**
```
Dhanyavaad. 🙏

Aisa lagta hai ki battery disconnect issue nahi hai.

Kripya thoda aur bataiye vehicle ki vartamaan sthiti kya hai.
```

**User describes naturally:**

Examples:
- "workshop mein hai"
- "accident ho gaya"
- "gps nikal gaya hai"
- "gps kharab hai"
- "vehicle chal rahi hai"
- "vehicle khadi hai"
- "driver leave par hai"

**Bot uses LLM to reclassify** → Routes to correct flow automatically

---

## Flow Diagram

```
Battery Disconnect → Q1: Battery maintenance?
                          ↓
                      ┌───┴───┐
                     YES     NO
                      ↓       ↓
                   Q2: Date   Q3: Describe situation
                      ↓           ↓
                   Close      LLM Reclassifies
                   Case           ↓
                              Routes to
                              correct flow
```

---

## LLM Understanding Examples

### Example 1: Battery Maintenance - Affirmative with Context
```
Bot: Kya battery maintenance, replacement ya repair ke liye disconnect ki gayi hai?

User: haan battery change ho rahi hai maintenance ke liye

LLM Analysis:
- Contains "battery change" (maintenance context)
- Contains "maintenance" (explicit)
- Intent: Battery maintenance
- Decision: YES

Bot: Vehicle ya battery system dobara kab operational hoga?
```

### Example 2: Battery Maintenance - Simple Affirmative
```
Bot: Kya battery maintenance, replacement ya repair ke liye disconnect ki gayi hai?

User: haan

LLM Analysis:
- Quick path: Simple "haan"
- Decision: YES (no LLM call needed)

Bot: Vehicle ya battery system dobara kab operational hoga?
```

### Example 3: NOT Battery Maintenance
```
Bot: Kya battery maintenance, replacement ya repair ke liye disconnect ki gayi hai?

User: nahi battery disconnect nahi hai galti se select ho gaya

LLM Analysis:
- Contains "nahi" (no)
- Contains "galti se" (mistake)
- Intent: Not battery maintenance
- Decision: NO

Bot: Dhanyavaad. 🙏
     Aisa lagta hai ki battery disconnect issue nahi hai.
     Kripya thoda aur bataiye vehicle ki vartamaan sthiti kya hai.
```

### Example 4: Reclassification - Workshop
```
Bot: Kripya thoda aur bataiye vehicle ki vartamaan sthiti kya hai.

User: vehicle workshop mein hai repair ke liye

LLM Reclassification:
- Classifies as: WORKSHOP
- Routes to: Workshop Flow

Bot: Kya vehicle filhaal workshop/service center mein repair ya maintenance ke liye hai?
```

### Example 5: Reclassification - GPS Removed
```
Bot: Kripya thoda aur bataiye vehicle ki vartamaan sthiti kya hai.

User: gps nikala hua hai testing ke liye

LLM Reclassification:
- Classifies as: GPS_REMOVED
- Routes to: GPS Removed Flow

Bot: Kya GPS device maintenance ya repair ke liye remove kiya gaya hai?
```

---

## LLM Implementation

### Function: `_is_battery_maintenance(text)`

```python
def _is_battery_maintenance(text: str) -> bool:
    """Check if battery maintenance is the reason using LLM understanding."""
    
    # Quick path for simple responses
    if text in ["haan", "yes", "ji"]:
        return True
    if text in ["nahi", "no"]:
        return False
    
    # LLM for natural language
    prompt = f"""Determine if battery is disconnected for maintenance/replacement/repair.

User was asked: "Kya battery maintenance, replacement ya repair ke liye disconnect ki gayi hai?"
User replied: "{text}"

Examples of YES:
- "maintenance ke liye nikali hai"
- "battery change ho rahi hai"
- "replacement chal raha hai"

Examples of NO:
- "nahi"
- "battery nahi nikali"
- "galti se select ho gaya"

Respond with ONLY: YES or NO"""

    response = generate_response(prompt).strip().upper()
    return response == "YES"
```

---

## Complete User Journey Examples

### Journey 1: Battery Maintenance Path
```
User: battery nikali hai

Bot: Dhanyavaad. 🙏
     Kya battery maintenance, replacement ya repair ke liye disconnect ki gayi hai?

User: haan battery change kar rahe hain

Bot: Vehicle ya battery system dobara kab operational hoga?
     Example: 20-06-2026

User: 22-06-2026

Bot: ✅ Dhanyavaad.
     Humne note kar liya hai ki battery maintenance/replacement ke kaaran vehicle inactive hai.
     Expected availability date: 📅 22-06-2026
     🙏 Thank You
     Case Status: Closed
```

### Journey 2: Reclassification to Workshop
```
User: 3

Bot: Dhanyavaad. 🙏
     Kya battery maintenance, replacement ya repair ke liye disconnect ki gayi hai?

User: nahi battery disconnect nahi hai

Bot: Dhanyavaad. 🙏
     Aisa lagta hai ki battery disconnect issue nahi hai.
     Kripya thoda aur bataiye vehicle ki vartamaan sthiti kya hai.

User: vehicle workshop mein hai repair ke liye

Bot: [Routes to Workshop Flow]
     Kya vehicle filhaal workshop/service center mein repair ya maintenance ke liye hai?
```

### Journey 3: Reclassification to GPS Removed
```
User: battery disconnect

Bot: Dhanyavaad. 🙏
     Kya battery maintenance, replacement ya repair ke liye disconnect ki gayi hai?

User: nahi galti se select ho gaya

Bot: Dhanyavaad. 🙏
     Aisa lagta hai ki battery disconnect issue nahi hai.
     Kripya thoda aur bataiye vehicle ki vartamaan sthiti kya hai.

User: gps nikal gaya hai

Bot: [Routes to GPS Removed Flow]
     Kya GPS device maintenance ya repair ke liye remove kiya gaya hai?
```

---

## Key Differences from Old Flow

### OLD Flow (Menu-Based):
```
Bot: Kya battery disconnect hai?
     1️⃣ Yes
     2️⃣ No

User: 2

Bot: [Shows 7-option menu]
     1️⃣ Workshop
     2️⃣ Accident
     3️⃣ GPS Removed
     ...
     
User: Must select number

Bot: [Routes to selected flow]
```

### NEW Flow (Conversational):
```
Bot: Kya battery maintenance ke liye disconnect ki gayi hai?

User: nahi

Bot: Kripya vehicle ki sthiti batayein.

User: gps nikal gaya hai (natural language)

Bot: [LLM reclassifies automatically]
     [Routes to GPS Removed Flow]
```

---

## Advantages of New Approach

### 1. No Menu Friction
- ❌ Old: User must select from 7 options
- ✅ New: User describes naturally, system understands

### 2. Faster Resolution
- ❌ Old: Extra menu step
- ✅ New: Direct reclassification

### 3. More Natural
- ❌ Old: "Select option 4"
- ✅ New: "gps nikal gaya hai"

### 4. Better UX
- ❌ Old: Feels like form filling
- ✅ New: Feels like conversation

### 5. Flexible Input
- ❌ Old: Must be number or exact keyword
- ✅ New: Any natural language description

---

## Reclassification Logic

### How It Works:

1. **User says NO to battery maintenance**
2. **Bot asks for situation description**
3. **User describes naturally**
4. **System uses `classify_customer_intent()`**
5. **Routes to classified flow automatically**

### Reclassification Examples:

| User Input | Classified As | Routes To |
|------------|---------------|-----------|
| "workshop mein hai" | WORKSHOP | Workshop Flow |
| "accident ho gaya" | ACCIDENT | Accident Flow |
| "gps nikal gaya" | GPS_REMOVED | GPS Removed Flow |
| "gps kharab hai" | GPS_DAMAGED | GPS Damaged Flow |
| "vehicle chal rahi hai" | VEHICLE_RUNNING | Vehicle Running Flow |
| "vehicle khadi hai" | VEHICLE_STANDING | Vehicle Standing Flow |
| "kuch aur problem hai" | UNKNOWN | Other Flow |

---

## Error Handling

### Case 1: LLM Service Unavailable
```python
try:
    response = generate_response(prompt)
    return response == "YES"
except Exception as e:
    logger.error(f"LLM failed: {str(e)}")
    # Fallback to keyword matching
    keywords = ["maintenance", "replacement", "change"]
    return any(kw in text.lower() for kw in keywords)
```

### Case 2: Invalid Date Format
```
User: kal

Bot: ⚠️ Invalid date format. Please use DD-MM-YYYY (Example: 20-06-2026)
```

### Case 3: Past Date
```
User: 10-06-2026

Bot: ⚠️ Purani date nahi select kar sakte.
     Kripya aaj ya future ki date dein.
     Example: 20-06-2026
```

---

## Language Support

### Supported Languages:
- ✅ **Hindi:** "battery maintenance ke liye nikali hai"
- ✅ **English:** "battery removed for maintenance"
- ✅ **Hinglish:** "battery change ho rahi hai repair ke liye"
- ✅ **Mixed:** "haan maintenance ke liye battery disconnect ki hai"

### Context Understanding:
The LLM understands:
- Synonyms: "maintenance", "replacement", "repair", "change"
- Actions: "nikali", "disconnect", "remove"
- Negations: "nahi", "not", "galti se"
- Mixed language sentences

---

## Sub-Steps

### Context Variables:
- `battery_sub_step`: Tracks position in flow
  - `None` → Initial maintenance question
  - `BATTERY_EXPECTED_DATE` → Waiting for date
  - `BATTERY_DESCRIBE_SITUATION` → Waiting for situation description

### State Storage:
```python
context = {
    "issue_classification": "BATTERY_DISCONNECT",
    "battery_sub_step": "BATTERY_EXPECTED_DATE",
    "battery_expected_date": "22-06-2026",
    "case_status": "CLOSED"
}
```

---

## Performance Optimization

### Quick Path (No LLM):
```python
# Simple responses bypass LLM
if text in ["haan", "yes", "ji"]:
    return True  # ~0ms

if text in ["nahi", "no"]:
    return False  # ~0ms
```

### LLM Path:
```python
# Complex responses use LLM
response = generate_response(prompt)  # ~200-500ms
return response == "YES"
```

### Fallback:
```python
# If LLM fails, keyword matching
except Exception:
    keywords = ["maintenance", "replacement", "change"]
    return any(kw in text for kw in keywords)
```

---

## Logging

### Decision Logging:
```
Battery: YES (LLM confirmed) - asking expected date for +918882374849
LLM battery maintenance check: 'battery change ho rahi hai' -> YES
```

```
Battery: NO (LLM confirmed) - asking for situation description for +918882374849
LLM battery maintenance check: 'nahi battery nahi nikali' -> NO
```

### Reclassification Logging:
```
Battery: Reclassifying from description: 'workshop mein hai' for +918882374849
Battery reclassification: 'workshop mein hai' -> WORKSHOP using LLM
```

---

## Files Modified

1. ✅ `app/services/flow_handlers/battery_flow.py`
   - Complete rewrite with LLM-driven understanding
   - Added `_is_battery_maintenance()` function
   - Added conversational reclassification logic
   - Removed menu-based reselection
   - Removed numbered options

2. ✅ `app/services/service_engineer_flow_service.py`
   - Updated initial Battery question
   - Removed "1️⃣ Yes\n2️⃣ No" options
   - Made it conversational

---

## Files NOT Modified

- ❌ Other flow handlers (workshop, accident, GPS, etc.)
- ❌ Database schema
- ❌ Ticket creation logic
- ❌ Engineer assignment logic
- ❌ APIs
- ❌ State management core
- ❌ Intent classification service (reused existing)

---

## Testing Scenarios

### Test 1: Battery Maintenance Path
```
Input (Q1): "haan battery change ho rahi hai"
Expected: Asks for expected date
LLM: YES
Result: ✅
```

### Test 2: Reclassification Path
```
Input (Q1): "nahi"
Input (Q2): "workshop mein hai"
Expected: Routes to Workshop Flow
Reclassification: WORKSHOP
Result: ✅
```

### Test 3: Natural Language YES
```
Input (Q1): "maintenance ke liye battery nikali hai"
Expected: Asks for expected date
LLM: YES
Result: ✅
```

### Test 4: Natural Language NO with Reclassification
```
Input (Q1): "battery disconnect nahi hai galti se select ho gaya"
Input (Q2): "gps nikal gaya hai testing ke liye"
Expected: Routes to GPS Removed Flow
Reclassification: GPS_REMOVED
Result: ✅
```

---

## Status: ✅ COMPLETE

The Battery Disconnect Flow is now fully conversational with intelligent LLM-driven understanding and automatic reclassification!

### Benefits:
1. ✅ **No Numbered Options** - Fully conversational
2. ✅ **Natural Language Understanding** - LLM interprets intent
3. ✅ **Automatic Reclassification** - No menu selection needed
4. ✅ **Multi-language Support** - Hindi/English/Hinglish
5. ✅ **Graceful Fallback** - Keyword matching if LLM fails
6. ✅ **Fast Performance** - Quick path for simple responses
7. ✅ **Better UX** - Feels natural and conversational
8. ✅ **Intelligent Routing** - Automatically routes to correct flow
