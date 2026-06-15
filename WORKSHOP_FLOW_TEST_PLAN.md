# Workshop Flow - Testing Guide

## Quick Test Scenarios

### Test 1: Workshop YES Path (Happy Path)
```
Step 1: Initial GPS Alert
📱 Bot sends: "GPS ALERT... Press 1 for AI assistance"
👤 You type: 1

Step 2: Q1 - Initial Question
📱 Bot sends: "Hello Sir, vehicle MH12AB1234... 
              1️⃣ Workshop
              2️⃣ Accident
              ..."
👤 You type: 1

Step 3: Q2 - Workshop Confirmation
📱 Bot sends: "Kya vehicle filhaal workshop mein hai?
              1️⃣ Yes
              2️⃣ No"
👤 You type: 1

Step 4: Q2a - Workshop Name
📱 Bot sends: "Kya aap workshop ka naam bata sakte hain?"
👤 You type: Sharma Auto Works

Step 5: Q2b - Duration
📱 Bot sends: "Vehicle workshop mein kab tak rehne ki sambhavana hai?
              1️⃣ 1-2 Din
              2️⃣ 3-7 Din
              3️⃣ 1 Hafte Se Zyada
              4️⃣ Pata Nahi"
👤 You type: 2

Step 6: Case Closed
📱 Bot sends: "Dhanyavaad.
              Workshop: Sharma Auto Works
              Duration: 3-7 Din
              Case Status: CLOSED
              END FLOW"
✅ TEST PASSED
```

---

### Test 2: Workshop NO Path → Reclassification to GPS Removed
```
Step 1-2: Same as Test 1 (initial alert → press 1 → select Workshop)

Step 3: Q2 - Workshop Confirmation
📱 Bot: "Kya vehicle workshop mein hai?"
👤 You type: 2 (No)

Step 4: Q2c - Detail Request
📱 Bot: "Kripya thoda aur detail mein batayein ki vehicle inactive kyon hai."
👤 You type: GPS nikal gaya hai

Step 5: LLM Reclassification
🤖 System classifies as: GPS_REMOVED

Step 6: Route to GPS Removed Flow (Q5)
📱 Bot: "GPS ko dobara install kab karwana hai?
        (Date & Time: DD/MM/YYYY HH:MM)"
✅ TEST PASSED - Successfully reclassified and routed
```

---

### Test 3: Workshop NO Path → Reclassification to GPS Damaged
```
Steps 1-3: Same (select Workshop → No)

Step 4: Q2c - Detail Request
👤 You type: GPS toot gaya hai

Step 5: LLM Reclassification
🤖 System classifies as: GPS_DAMAGED

Step 6: Route to GPS Damaged Flow (Q10)
📱 Bot: "Vehicle ki current location kya hai?"
✅ TEST PASSED
```

---

### Test 4: Workshop NO Path → Reclassification to Battery
```
Steps 1-3: Same (select Workshop → No)

Step 4: Q2c
👤 You type: Battery nikali hui hai maintenance ke liye

Step 5: Reclassification
🤖 System classifies as: BATTERY_DISCONNECT

Step 6: Route to Battery Flow (Q4)
📱 Bot: "Kya battery maintenance ke liye disconnect ki gayi hai?"
✅ TEST PASSED
```

---

### Test 5: Invalid Input Handling
```
Q2: Workshop confirmation
👤 You type: maybe (invalid)
📱 Bot: "⚠️ Kripya valid option select karein.
        1️⃣ Yes
        2️⃣ No"
✅ TEST PASSED - Error handling works

Q2a: Workshop name
👤 You type: S (too short)
📱 Bot: "⚠️ Kripya workshop ka naam batayein."
✅ TEST PASSED

Q2b: Duration
👤 You type: 7 (invalid option)
📱 Bot: "⚠️ Kripya 1, 2, 3, ya 4 select karein."
✅ TEST PASSED
```

---

### Test 6: Numeric vs Text Input for Initial Selection
```
Test 6a: Numeric input
👤 You type: 1
📱 Bot routes to Workshop flow
✅ PASS

Test 6b: Text input (Hindi)
👤 You type: workshop
📱 Bot should still route to Workshop flow via LLM
✅ PASS

Test 6c: Text input (English)
👤 You type: vehicle workshop mein hai
📱 Bot should route to Workshop flow via regex/LLM
✅ PASS
```

---

## Expected Behavior Summary

### Workshop Flow Entry Points:
1. **Numeric selection:** User types "1" at Q1
2. **Text selection (Hindi):** workshop, वर्कशॉप
3. **Text selection (English):** workshop, repair center, service center

### Workshop Flow Exit Points:
1. **Case Closed:** YES path → Workshop name → Duration → CLOSED
2. **Reclassification:** NO path → Detail → LLM classifies → Route to:
   - Accident Flow (Q3)
   - Battery Flow (Q4)
   - GPS Removed Flow (Q5)
   - GPS Damaged Flow (Q10)
   - Vehicle Running Flow (Q13)
   - Vehicle Standing Flow (Q17)
   - Other Flow (Q20)

### Context Fields Stored:
```python
{
    "issue_classification": "WORKSHOP",
    "workshop_sub_step": "WORKSHOP_NAME" | "WORKSHOP_DURATION" | "WORKSHOP_DETAIL_REQUEST",
    "workshop_name": "Sharma Auto Works",
    "workshop_duration": "3-7 Din",
    "reclassified_from": "WORKSHOP",  # if reclassified
    "reclassified_to": "GPS_REMOVED",  # if reclassified
    "reclassification_detail": "GPS nikal gaya hai"  # if reclassified
}
```

---

## How to Test Manually

### Option 1: Using WhatsApp Test Number
1. Send GPS alert to test number
2. Follow the prompts
3. Verify responses match expected behavior

### Option 2: Using API Testing Tool (Postman/cURL)
```bash
# Step 1: Simulate pressing "1"
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "From": "whatsapp:+15556394633",
    "Body": "1"
  }'

# Step 2: Select Workshop (option 1)
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "From": "whatsapp:+15556394633",
    "Body": "1"
  }'

# Step 3: Confirm YES
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "From": "whatsapp:+15556394633",
    "Body": "1"
  }'

# Step 4: Provide workshop name
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "From": "whatsapp:+15556394633",
    "Body": "Sharma Auto Works"
  }'

# Step 5: Select duration
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "From": "whatsapp:+15556394633",
    "Body": "2"
  }'

# Expected: Case closed message
```

---

## Logging & Debugging

### Key Log Messages to Watch:
```
INFO: User pressed 1 for AI assistance (no active flow)
INFO: Intent classified as WORKSHOP using NUMERIC
INFO: Workshop: YES - asking workshop name for +15556394633
INFO: Workshop: Name received - Sharma Auto Works for +15556394633
INFO: Workshop: Duration 3-7 Din - closing case for +15556394633
```

### For NO path reclassification:
```
INFO: Workshop: NO - asking for details for +15556394633
INFO: Workshop: Reclassifying based on detail - GPS nikal gaya hai for +15556394633
INFO: Workshop: Reclassified as GPS_REMOVED using LLM
```

---

## Success Criteria

✅ **Workshop Flow is COMPLETE when:**
1. User can select option 1 (Workshop) from Q1
2. User can confirm YES and provide workshop details
3. Case closes with workshop name and duration shown
4. User can select NO and provide additional details
5. System successfully reclassifies and routes to correct flow
6. Invalid inputs show appropriate error messages
7. All conversation state is properly stored and cleared
8. No Python errors or exceptions occur

---

**Next Steps After Workshop Testing:**
1. Implement Accident Flow (similar pattern)
2. Implement Battery Flow (similar pattern)
3. Test all 8 flows end-to-end
4. Test Service Request Collector (SMART field collection)
5. Test Engineer Assignment (Q35)
