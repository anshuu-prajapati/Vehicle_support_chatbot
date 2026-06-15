# Testing Guide - GPS Service Engineer Flow

## Your Original Issue - Now Fixed ✅

**Before (Error):**
```
[1:40 pm] Bot: GPS ALERT - Vehicle MH12AB1234
[1:40 pm] User: 1
[1:40 pm] Bot: Where is vehicle, why inactive?
[1:40 pm] User: delhi gps khrab ho gya
[1:40 pm] Bot: ✅ GPS Damaged - Current location?
[1:41 pm] User: delhi, kirti nagar
[1:41 pm] Bot: Flow handler not yet implemented. ❌
```

**After (Working):**
```
[1:40 pm] Bot: GPS ALERT - Vehicle MH12AB1234
[1:40 pm] User: 1
[1:40 pm] Bot: Where is vehicle, why inactive?
[1:40 pm] User: delhi gps khrab ho gya
[1:40 pm] Bot: ✅ GPS Damaged - Current location?
[1:41 pm] User: delhi, kirti nagar
[1:41 pm] Bot: ✅ Location noted
              Q12: GPS physically damage hua?
              1️⃣ Yes  2️⃣ No
[1:41 pm] User: 1
[1:41 pm] Bot: Q13: GPS replacement zarurat hai?
              1️⃣ Yes  2️⃣ No
[1:42 pm] User: 1
[1:42 pm] Bot: 📋 Service request - Q25: Vehicle number?
...continues through all questions...
```

## Complete Test Script

### Test 1: GPS Damaged Flow (Your Case)

```
Step 1: Trigger alert or type "1"
Step 2: "delhi gps khrab ho gya"
Step 3: "delhi, kirti nagar"
Step 4: "1" (yes, physically damaged)
Step 5: "1" (yes, need replacement)
Step 6: Answer Q25-Q34 (vehicle details)
Step 7: "1" (assign engineer)

Expected: Ticket created, engineer assigned
```

### Test 2: Workshop Flow

```
User: "vehicle workshop mein hai"
Bot: Q3 - Workshop mein repair ke liye?
User: "1" (yes)
Expected: Case closed (no service needed)
```

### Test 3: Battery Flow

```
User: "battery disconnect hai"
Bot: Q6 - Maintenance ke liye disconnect?
User: "1" (yes)
Bot: Q7 - GPS dobara install karna hai?
User: "1" (yes)
Expected: Service request flow starts
```

### Test 4: GPS Removed Flow

```
User: "gps nikaal diya"
Bot: Q10 - Kisne remove kiya?
User: "1" (customer)
Bot: Q11 - Dobara install karwana hai?
User: "1" (yes)
Expected: Service request flow starts
```

### Test 5: Vehicle Standing Flow

```
User: "vehicle khadi hai"
Bot: Q14 - Kitne samay se?
User: "3" (>48 hours)
Bot: Q15 - Inspection zarurat hai?
User: "1" (yes)
Expected: Service request flow starts
```

### Test 6: Vehicle Running Flow

```
User: "vehicle chal rahi hai lekin gps nahi aa raha"
Bot: Q18 - Driver ka naam?
User: "Ramesh"
Bot: Q19 - Driver ka mobile?
User: "9876543210"
Bot: Q20 - Current location?
User: "Mumbai, Andheri"
Bot: Q21 - Inspection ke liye available?
User: "1" (yes)
Expected: Service request flow starts
```

### Test 7: Accident Flow

```
User: "accident ho gaya"
Bot: Q5 - GPS device damage hua?
User: "1" (yes)
Expected: Service request flow starts
```

### Test 8: Other Issue Flow

```
User: "kuch aur problem hai"
Bot: Q23 - Issue describe karein
User: "wire loose ho gayi hai"
Bot: Q24 - GPS se related hai?
User: "1" (yes)
Expected: Service request flow starts
```

## Service Request Data Collection Test

When any flow triggers service request, test Q25-Q34:

```
Q25 (Vehicle Number):
  - Valid: "MH12AB1234" ✅
  - Invalid: "123" ❌ (too short)

Q26 (Owner Name):
  - Valid: "Anshu Kumar" ✅
  - Invalid: "A" ❌ (too short)

Q27 (Owner Mobile):
  - Valid: "9876543210" ✅
  - Valid: "+919876543210" ✅
  - Invalid: "123" ❌

Q28 (Location):
  - Valid: "Delhi, Kirti Nagar, Near Metro Station" ✅
  - Invalid: "Dlh" ❌ (too short)

Q29 (Driver Name):
  - Valid: "Ramesh" ✅
  - Valid: "NA" ✅ (no driver)

Q30 (Driver Mobile):
  - Valid: "9876543210" ✅
  - Valid: "NA" ✅

Q31 (Vehicle Available):
  - "1" (yes) → asks visit date/time
  - "2" (no) → asks visit date/time

Q32 (Visit Date):
  - Valid: "15/06/2026" ✅
  - Valid: "15-06-2026" ✅
  - Invalid: "15/13/2026" ❌ (invalid month)
  - Invalid: "10/05/2020" ❌ (past date)

Q33 (Visit Time):
  - Valid: "10:00 AM" ✅
  - Valid: "14:30" ✅
  - Valid: "2 PM" ✅
  - Invalid: "25:00" ❌

Q34 (Issue Type):
  - "1" → GPS Not Working
  - "2" → GPS Removed
  - "3" → GPS Damaged
  - "4" → Battery Related
  - "5" → GPS Reinstallation
  - "6" → Accident Related
  - "7" → Other
```

## Engineer Assignment Test (Q35)

```
After Q34, bot shows summary:
Bot: 📋 Summary:
     Vehicle: MH12AB1234
     Owner: Anshu
     ...
     
     Q35: Assign nearest engineer?

Test A: User says "1" (yes)
  Expected: 
    - Ticket created
    - Status = ASSIGNED
    - Engineer notification sent
    - User gets confirmation with ticket number

Test B: User says "2" (no)
  Expected:
    - Ticket created
    - Status = ON_HOLD
    - User gets confirmation
    - No engineer assigned yet
```

## Error Handling Tests

### Test Reset Command
```
At any point in conversation:
User: "reset"
Expected: Conversation cleared, can start fresh
```

### Test Invalid Input
```
When bot asks yes/no:
User: "maybe"
Expected: Error message, re-ask question
```

### Test Date Validation
```
Q32 - Visit Date:
User: "yesterday"
Expected: Error, ask for DD/MM/YYYY format
```

## Database Verification

After successful flow completion, check database:

```sql
-- Check ticket created
SELECT * FROM tickets WHERE vehicle_number = 'MH12AB1234' ORDER BY created_at DESC LIMIT 1;

-- Verify fields populated
SELECT 
  ticket_number,
  issue_type,
  vehicle_number,
  owner_name,
  owner_mobile,
  driver_name,
  driver_mobile,
  location,
  visit_date,
  visit_time,
  vehicle_available,
  status,
  assigned_engineer_id
FROM tickets 
WHERE ticket_number = 'TKT-XXXX';

-- Check conversation state cleared
SELECT * FROM conversation_states WHERE phone_number = '+15556394633';
```

## Expected Ticket Status Flow

```
OPEN → Data collection in progress
  ↓
ASSIGNED → Engineer assigned (Q35: Yes)
  ↓
IN_PROGRESS → Engineer working on it
  ↓
RESOLVED → Issue fixed
  ↓
CLOSED → Ticket closed

OR

OPEN → ON_HOLD → (Q35: No)
```

## Logging Verification

Check logs for proper flow execution:

```bash
# View recent logs
tail -f app.log | grep "service_engineer"

# Should see entries like:
# - "Intent classified as GPS_DAMAGED"
# - "GPS replacement needed - service request"
# - "Engineer assignment: Ticket assigned"
```

## Performance Checks

- Response time < 2 seconds per message
- No memory leaks (conversation state cleared after completion)
- Database queries optimized (pre-fill from DB in single query)

## Common Issues to Watch For

1. **Conversation state not clearing**: Check if `clear_state()` is called
2. **Fields not pre-filling**: Verify user has associated vehicle in DB
3. **Date/time parsing fails**: Check format validation logic
4. **Engineer assignment fails**: Verify engineer exists in users table

## Success Criteria

✅ All 8 flows complete without errors
✅ Service request collects all required fields
✅ Validation catches invalid inputs
✅ Tickets created with correct data
✅ Conversation state properly managed
✅ User receives clear confirmation messages
✅ No "Flow handler not yet implemented" errors

## Your Specific Test

**Run your exact conversation:**

```
Message 1: "1"
Message 2: "delhi gps khrab ho gya"
Message 3: "delhi, kirti nagar"
Message 4: "1"  (GPS damaged)
Message 5: "1"  (need replacement)
Message 6-15: Answer service request questions
Message 16: "1"  (assign engineer)

Expected Result: 
✅ Ticket TKT-XXXX created
✅ Engineer assigned
✅ Confirmation message sent
✅ No errors
```

Ready to test! 🚀
