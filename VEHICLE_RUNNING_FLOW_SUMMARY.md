# Vehicle Running Flow - Quick Reference

## ✅ Status: COMPLETE

## What Changed

### OLD Flow (Option-Based):
```
User selects "6" → Bot asks for Driver Name → Driver Mobile → Location → Date/Time → Service Request
```

### NEW Flow (Conversational):
```
User says "gaadi chal rahi hai" or selects "6" 
→ Bot asks for Location 
→ Natural language Date/Time 
→ Contact Confirmation (LLM)
→ Optional Additional Info
→ Service Request Created
```

---

## 4 Questions Flow

### Q1: Location
```
Kripya vehicle ki current location bata dijiye jahan inspection karwana hai.
📍 Example: Kirti Nagar, Delhi
```
**User:** "Andheri East, Mumbai"

---

### Q2: Date/Time (Natural Language)
```
Vehicle inspection ke liye kab available rahegi?
Examples: Kal subah, 22 June, Monday afternoon
```
**User:** "Kal subah" → LLM converts to: 17-06-2026, 10:00

---

### Q3: Contact Confirmation
```
Humare records ke anusaar registered mobile number:
📱 9876543210
Agar isi number par sampark karna hai to "Theek Hai" likhein.
```
**User:** "Theek Hai" → LLM understands: Use same number
**OR User:** "9123456789" → LLM understands: Use alternate

---

### Q4: Additional Info (Optional)
```
Agar driver ka naam ya koi additional jankari share karna chahte hain...
(Yeh optional hai.)
```
**User:** "Driver Ramesh hai" → Saved
**OR User:** "Nahi" → Skipped

---

## Key Features

✅ **No Numbered Options** - Removed all 1️⃣ 2️⃣ buttons
✅ **Natural Date/Time** - "Kal subah", "22 June", "Monday afternoon"
✅ **No Mandatory Driver Info** - Completely optional
✅ **LLM Contact Understanding** - Understands "Theek Hai", "same", etc.
✅ **Enhanced Error Handling** - Detailed logging for debugging
✅ **Always Creates Service Request** - No case closure in this flow

---

## Files Modified

1. **`app/services/flow_handlers/vehicle_running_flow.py`**
   - Created complete LLM-driven implementation
   - Added `_parse_natural_datetime()` - LLM date/time parsing
   - Added `_wants_same_contact()` - LLM contact confirmation
   - Enhanced error handling in service request creation

2. **`app/services/service_engineer_flow_service.py`**
   - Updated routing for Vehicle Running (option 6)
   - Changed initial question to conversational format

---

## Testing Examples

### Example 1: Complete Flow
```
User: "6" [selects Vehicle Running]
Bot: "Kripya vehicle ki current location..."
User: "Kirti Nagar, Delhi"
Bot: "Vehicle inspection ke liye kab..."
User: "Kal subah"
Bot: "Humare records ke anusaar 9876543210..."
User: "Theek Hai"
Bot: "Agar driver ka naam..."
User: "Driver Mohan hai, gate 3 ke paas"
Bot: "✅ Service request created! Ticket: TKT-1234"
```

### Example 2: Natural Language Selection
```
User: "Gaadi chal rahi hai par GPS nahi aa raha"
Bot: "Kripya vehicle ki current location..." [Auto-routed to Vehicle Running]
```

---

## Important Notes

- **Date must be today or future** - Past dates rejected
- **Location minimum 5 characters** - Validates address length
- **Phone validation** - 10-15 digits for alternate numbers
- **LLM fallback** - Keyword matching if LLM fails
- **Conversation clears** - State cleared after service request creation
- **High priority** - Service requests created with HIGH priority

---

## Error Messages

| Scenario | Message |
|----------|---------|
| Location too short | ⚠️ Kripya pura address dein. |
| Past date | ⚠️ Purani date nahi select kar sakte. |
| Invalid date format | ⚠️ Kripya date aur time clear format mein dein |
| Invalid phone | ⚠️ Kripya valid mobile number dein. |
| Service creation failed | ⚠️ Service request create karne mein error aaya. |

---

**Status:** Ready for Testing ✅
**Date:** June 16, 2026
