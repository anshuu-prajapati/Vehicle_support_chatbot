# Vehicle Standing Flow - LLM Conversational Implementation

## Status: ✅ COMPLETE

## Overview
The Vehicle Standing Flow has been completely redesigned to be fully conversational, LLM-driven, with clarification support. All numbered options have been removed, and the flow now asks only ONE question with natural language understanding.

---

## Major Changes

### OLD Flow (Complex, 3 Questions):
```
Q1: Vehicle kitne samay se khadi hai?
    1️⃣ Less than 24 hrs
    2️⃣ 24-48 hrs
    3️⃣ More than 48 hrs

If Option 3 (>48 hrs):
  → Close case

If Option 1 or 2 (<48 hrs):
  Q2: Vehicle ki current location kya hai?
  Q3: Vehicle inspection ke liye kab available hai? (DD/MM/YYYY HH:MM)
  → Service Request Created
```

### NEW Flow (Simple, 1 Question):
```
Q1: Vehicle lagbhag kab tak dobara chalne lagegi?
    Examples: Kal, 2 din baad, Agle hafte, 25 June, Pata nahi

If date provided:
  → Close case with expected date ✅

If "don't know":
  → Close case without date ✅

NO service request created
NO additional questions
```

---

## Flow Design

### Customer Says:
- "Vehicle khadi hai"
- "Gaadi use nahi ho rahi"
- "Driver leave par hai"
- "Vehicle standing hai"
- "Park karke rakhi hai"

### LLM Classifies:
`VEHICLE_STANDING`

---

## Conversation Flow

### Question (Only One):
**Bot:**
```
Dhanyavaad. 🙏

Kya aap bata sakte hain vehicle lagbhag kab tak dobara chalne lagegi?

📅 Example:
• Kal
• 2 din baad
• Agle hafte
• 25 June
• Pata nahi
```

---

### Path A: User Provides Expected Date

**User Response:**
- "Kal"
- "3 din baad"
- "Agle Monday"
- "25 June"
- "Do hafte baad"

**LLM Processing:**
- Converts natural language to date
- Uses current date as reference
- Handles Hindi, English, Hinglish

**Bot Response:**
```
✅ Dhanyavaad.

Humne note kar liya hai ki vehicle filhaal standing condition mein hai.

Expected operational date: 📅 {expected_date}

Is samay kisi service engineer ki avashyakta nahi hai.

Agar vehicle dobara chalne ke baad bhi GPS issue rahta hai,
to aap support request raise kar sakte hain.

🙏 Thank You

Case Status: Closed
```

---

### Path B: User Doesn't Know Date

**User Response:**
- "Pata nahi"
- "Confirm nahi hai"
- "Abhi nahi pata"
- "Driver batayega"
- "Date fix nahi hai"
- "Don't know"
- "Not sure"

**LLM Detection:**
- Recognizes uncertainty keywords
- Understands various "don't know" phrases

**Bot Response:**
```
Koi baat nahi. 😊

Jab vehicle dobara operational ho jaye aur GPS issue continue rahe,
to aap humse sampark kar sakte hain.

Humne is case ko filhaal standing vehicle ke roop mein note kar liya hai.

🙏 Thank You

Case Status: Closed
```

---

## Clarification Support

### If User Confused:

**User:**
- "Mujhe samajh nahi aaya"
- "Kya matlab?"
- "Kyun pooch rahe ho?"
- "Explain karo"

**Bot (Using Clarification Handler):**
```
Koi baat nahi. 😊

Hum sirf yeh jaan na chahte hain ki vehicle lagbhag kab dobara chalne lagegi.

Isse humein samajhne mein madad milti hai ki GPS issue vehicle standing hone 
ki wajah se hai ya kisi technical issue ki wajah se.

Kripya bata dijiye vehicle kab tak dobara operational ho sakti hai.
```

**[STAYS ON SAME STEP - Does not advance workflow]**

---

## Technical Implementation

### File: `app/services/flow_handlers/vehicle_standing_flow.py`

#### Key Functions:

**1. `_parse_expected_running_date(text: str) -> tuple`**
Parses natural language date input.

**Returns:**
- `(parsed_date, None, True)` - Date successfully parsed
- `(None, None, False)` - User doesn't know
- `(None, error_message, None)` - Parsing error

**Examples:**
```python
_parse_expected_running_date("kal") → (tomorrow_date, None, True)
_parse_expected_running_date("pata nahi") → (None, None, False)
_parse_expected_running_date("agle hafte") → (next_monday, None, True)
```

**LLM Prompt:**
```
Extract expected running date from natural language.

Today's date: {today}
User said: "{text}"

Examples:
- "kal" → Tomorrow
- "2 din baad" → Day after tomorrow
- "agle hafte" → Next week Monday
- "25 June" → 25/06/2026
- "pata nahi" → NO_DATE_AVAILABLE

Respond: DATE: DD/MM/YYYY or NO_DATE_AVAILABLE
```

**Don't Know Keywords Detected:**
- pata nahi
- nahi pata
- confirm nahi
- don't know
- not sure
- uncertain
- abhi nahi pata
- driver batayega
- fix nahi
- decide nahi

---

**2. `handle_vehicle_standing_flow(...)`**
Main flow handler with integrated clarification support.

**Flow Logic:**
1. Check if clarification needed (using clarification handler)
2. If clarification needed → Explain and stay on step
3. Otherwise → Parse expected date
4. If date parsed → Close case with date
5. If user doesn't know → Close case without date
6. If parsing error → Show error message

---

### File: `app/services/service_engineer_flow_service.py`

**Updated Initial Question:**

**Before:**
```
Vehicle kitne samay se khadi hai?
1️⃣ 24 ghante se kam
2️⃣ 24-48 ghante
3️⃣ 48 ghante se adhik
```

**After:**
```
Dhanyavaad. 🙏

Kya aap bata sakte hain vehicle lagbhag kab tak dobara chalne lagegi?

📅 Example:
• Kal
• 2 din baad
• Agle hafte
• 25 June
• Pata nahi
```

---

## Key Improvements

### ✅ Simplified Flow
- **Before:** 3 questions with options and service request
- **After:** 1 question with natural language → Case closed

### ✅ No Service Request
- Standing vehicles don't need service engineer
- Just record expected operational date
- Closes case immediately

### ✅ Natural Language Support
- "Kal" → Understands as tomorrow
- "2 din baad" → Day after tomorrow
- "Agle Monday" → Next Monday
- "25 June" → Specific date

### ✅ Handles Uncertainty
- "Pata nahi" → Recognized and handled gracefully
- Doesn't force user to provide date
- Closes case even without date

### ✅ Clarification Recovery
- Integrated with global clarification handler
- Detects confusion/questions
- Explains context without advancing workflow

---

## Intent Classification

User can trigger this flow by saying:

### Natural Language Examples:
- "Vehicle khadi hai"
- "Gaadi use nahi ho rahi"
- "Driver leave par hai"
- "Vehicle standing hai"
- "Park karke rakhi hai"
- "Vehicle currently idle hai"
- "Gaadi chal nahi rahi"

### Numeric Selection:
- "7" → Direct route to Vehicle Standing

LLM classifies as: **VEHICLE_STANDING**

---

## Testing Scenarios

### Scenario 1: User Provides Specific Date
```
Bot: "Vehicle lagbhag kab tak dobara chalne lagegi?"
User: "25 June"
Bot: "✅ Expected operational date: 25-06-2026. Case Status: Closed"
```

### Scenario 2: User Says Tomorrow
```
Bot: "Vehicle lagbhag kab tak dobara chalne lagegi?"
User: "Kal"
Bot: "✅ Expected operational date: 17-06-2026. Case Status: Closed"
```

### Scenario 3: User Says "Don't Know"
```
Bot: "Vehicle lagbhag kab tak dobara chalne lagegi?"
User: "Pata nahi"
Bot: "Koi baat nahi. 😊 Jab operational ho jaye... Case Status: Closed"
```

### Scenario 4: User Confused
```
Bot: "Vehicle lagbhag kab tak dobara chalne lagegi?"
User: "Kyun pooch rahe ho?"
Bot: [Clarification] "Hum sirf yeh jaan na chahte hain..."
[STAYS ON SAME STEP]
User: "Agle hafte"
Bot: "✅ Expected operational date: 23-06-2026. Case Status: Closed"
```

---

## Comparison with OLD Flow

| Aspect | OLD | NEW |
|--------|-----|-----|
| Questions | 3 (Duration, Location, Date/Time) | 1 (Expected running date) |
| Options | Numbered 1-3 | Natural language |
| Service Request | Created if <48 hrs | Never created |
| Location | Asked separately | Not needed |
| Inspection Date | Strict format DD/MM/YYYY HH:MM | Natural: "kal", "agle hafte" |
| Uncertainty | Not handled | "Pata nahi" accepted |
| Clarification | Not supported | Fully supported |
| Case Closure | Only if >48 hrs | Always closes case |

---

## Business Logic Changes

### Why No Service Request?

**Old Logic:**
- If vehicle standing <48 hrs → Create service request
- Assumption: Needs engineer visit

**New Logic:**
- Standing vehicles just need time to run again
- GPS will work when vehicle moves
- No engineer visit needed
- Just record expected operational date
- User can contact if issue persists after running

---

## Data Stored

### In Context:
```python
{
    "standing_expected_date": "25-06-2026",  # If date provided
    "standing_status": "UNKNOWN_DATE",        # If date not known
    "case_status": "CLOSED"
}
```

### No Ticket Created
- Standing vehicles don't create tickets
- Case simply closed with notes

---

## Error Handling

### Invalid Date Input:
```
User: "xyz abc"
Bot: "⚠️ Kripya date thoda clear format mein bataiye (Example: kal, 2 din baad, 25 June)"
```

### Past Date:
```
User: "10 June" (if today is 17 June)
Bot: "⚠️ Purani date nahi select kar sakte"
```

### Unclear Response:
```
User: [Something unclear]
Bot: "⚠️ Kripya thoda clear bataiye vehicle kab tak operational ho sakti hai"
```

---

## Important Notes

1. **Always closes case** - No service request path
2. **Accepts uncertainty** - "Pata nahi" is valid response
3. **Natural language only** - No strict formats
4. **Clarification supported** - Integrated with global handler
5. **Simple and fast** - Only 1 question vs 3 questions

---

## Completion Checklist

- [x] Remove numbered options (1️⃣ 2️⃣ 3️⃣)
- [x] Remove location question
- [x] Remove inspection date/time question
- [x] Remove service request creation
- [x] Implement natural language date parsing
- [x] Handle "don't know" responses
- [x] Integrate clarification handler
- [x] Update routing in service_engineer_flow_service.py
- [x] Simplified to 1 question only
- [x] Always close case (no service request path)
- [x] Support Hindi/English/Hinglish

---

## Next Steps

The Vehicle Standing Flow is now complete and ready for testing. When testing:

1. Test with various natural language dates
2. Test "pata nahi" and variations
3. Test clarification with "kyun pooch rahe ho"
4. Verify case closes properly
5. Confirm no service request created
6. Monitor logs for any unexpected behavior

---

**Last Updated:** June 17, 2026
**Status:** COMPLETE ✅
