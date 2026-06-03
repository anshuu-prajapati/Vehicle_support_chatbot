# AI Support System - Complete Test Workflow

This document provides step-by-step testing instructions for the complete vehicle alert management workflow.

## Quick Start

### 1. Setup Database
```bash
# Run this from project root
python scripts/seed_dummy_data.py
```

**Output:**
```
📌 Creating test users...
✓ Created manager: +918882374849 (Manager Raj)
✓ Created driver 1: +918290323758 (Driver Amit)
✓ Created driver 2: +919876543210 (Driver Vikram)
✓ Created contact: +919988776655 (Contact Priya)

🚗 Creating test vehicles...
✓ Created vehicle 1: DL-01-AB-1234
✓ Created vehicle 2: DL-02-CD-5678

🔧 Creating vehicle status...
✓ Vehicle 1 status: off / not working at Noida Depot
✓ Vehicle 2 status: on / working at Highway NH-1 Near Gurugram

🎓 Creating problems and solutions...
✓ Problems and solutions seeded successfully

🚨 Detecting alerts...
✓ Detected and created 1 alert(s)
```

## Complete Workflow Test

### Test Scenario: Vehicle NOT WORKING Alert → Manager Investigation → Driver Troubleshooting

```
GTRAC API
    ↓
Fetch Vehicle Data (ign_state='off', mode='not working')
    ↓
Store Latest Status (VehicleStatus)
    ↓
Check Alert Rules (ign_state='off' AND mode='not working')
    ↓
[ALERT TRIGGERED]
    ↓
Create Alert Record (alerts table)
    ↓
Create Conversation State (FLEET_ALERT_CREATED)
    ↓
Find Assigned Manager
    ↓
Send WhatsApp Alert to Manager
    ↓
[MANAGER REPLIES]
    ├─→ Option 1: "1" → HANDLE ALERT
    ├─→ Option 2: "2" → TRANSFER TO ANOTHER PERSON
    └─→ Option 3: "3" → CONTACT DRIVER
```

---

## Step-by-Step Testing Guide

### **STEP 1: Verify Alert Detection**

#### Database Setup Check
```sql
-- Check managers
SELECT id, name, phone_number, role FROM users WHERE role='manager' LIMIT 5;

-- Check drivers  
SELECT id, name, phone_number, role FROM users WHERE role='customer' LIMIT 5;

-- Check vehicles
SELECT id, vehicle_number, manager_id, driver_id FROM vehicles;

-- Check vehicle status (should have one NOT WORKING)
SELECT v.vehicle_number, vs.ign_state, vs.mode, vs.location, vs.last_gps_time 
FROM vehicle_status vs
JOIN vehicles v ON vs.vehicle_id = v.id;

-- Check alerts created
SELECT id, vehicle_id, status, alert_type, created_at FROM alerts;
```

#### Expected Results:
```
Vehicle 1: ign_state='off', mode='not working' ← Alert should be created
Vehicle 2: ign_state='on', mode='working' ← No alert
Alert count: 1 (for Vehicle 1)
```

#### Verify Conversation State Created:
```sql
SELECT * FROM conversation_states 
WHERE phone_number='+918882374849' 
ORDER BY created_at DESC LIMIT 1;
```

**Expected:**
- `phone_number`: +918882374849 (Manager's number)
- `current_step`: FLEET_ALERT_CREATED
- `context_json`: Contains alert_id, vehicle_number, driver_name, location, etc.

---

### **STEP 2: Manager Receives WhatsApp Alert**

#### Alert Message Format:
```
🚨 **FLEET ALERT**

Vehicle DL-01-AB-1234 NOT WORKING!

📋 **Details:**
• Driver: Driver Amit
• Location: Noida Depot
• Last GPS Update: 2024-01-15 14:30:45

**Kya aap is alert ko handle karenge?**
1. Haan, main handle karunga
2. Kisi aur ko assign karo
3. Driver ko directly contact karo

Reply with: 1, 2, or 3
```

#### Manager Database State:
```sql
SELECT ps.phone_number, ps.current_step, ps.context_json 
FROM conversation_states ps 
WHERE phone_number='+918882374849';
```

**Expected:**
- `current_step`: FLEET_ALERT_CREATED
- `context_json` contains vehicle details

---

### **STEP 3a: Manager Option 1 - "I am responsible" (Reply: 1)**

#### Manager Sends Reply:
```
Message: "1"
Phone: +918882374849 (via WhatsApp)
```

#### Bot Response:
```
Thank you! I will now contact the driver to investigate.
```

#### Database State After Reply:
```sql
-- Check conversation state transition
SELECT ps.phone_number, ps.current_step, ps.context_json, ps.updated_at
FROM conversation_states ps
WHERE phone_number='+918882374849'
ORDER BY ps.updated_at DESC LIMIT 1;

-- Check chat history
SELECT phone_number, user_message, bot_response, created_at FROM chat_messages
WHERE phone_number='+918882374849'
ORDER BY created_at DESC LIMIT 3;
```

**Expected After Step 3a:**
- `current_step`: CONTACT_DRIVER (transition from FLEET_ALERT_CREATED)
- `chat_messages`: Manager's "1" and bot's "Thank you!" response
- New message will be sent to driver

---

### **STEP 3b: Manager Option 2 - "Transfer" (Reply: 2)**

#### Manager Sends Reply:
```
Message: "2"
Phone: +918882374849 (via WhatsApp)
```

#### Bot Response:
```
Please provide the name and phone number of the person to transfer this to.

Format: Name | Phone
Example: Priya | +919988776655
```

#### Database State After Reply:
```sql
SELECT ps.current_step, ps.context_json 
FROM conversation_states ps
WHERE phone_number='+918882374849'
ORDER BY ps.updated_at DESC LIMIT 1;
```

**Expected:**
- `current_step`: WAITING_NEW_CONTACT_NAME

#### Manager Provides Transfer Details:
```
Message: "Priya | +919988776655"
```

#### Database After Transfer Accepted:
```sql
-- Old manager state
SELECT * FROM conversation_states 
WHERE phone_number='+918882374849' 
ORDER BY updated_at DESC LIMIT 1;

-- New contact person state
SELECT * FROM conversation_states 
WHERE phone_number='+919988776655' 
ORDER BY created_at DESC LIMIT 1;

-- Transfer history in context
SELECT ps.context_json FROM conversation_states 
WHERE phone_number='+919988776655' LIMIT 1;
```

**Expected:**
- New contact person (+919988776655) has FLEET_ALERT_CREATED state
- Transfer history recorded in context_json
- Original manager state updated

---

### **STEP 3c: Manager Option 3 - "Contact Driver" (Reply: 3)**

#### Manager Sends Reply:
```
Message: "3"
Phone: +918882374849 (via WhatsApp)
```

#### Bot Response to Manager:
```
Okay! I will contact the driver directly now.
```

#### Driver Receives Alert:
```
🚗 Vehicle DL-01-AB-1234 has stopped.

Driver Amit, is this your vehicle?

Kripaya confirm:
1. Haan, ye mera vehicle hai
2. Nahi, ye mera vehicle nahi hai

Reply with: 1 or 2
```

#### Database State:
```sql
-- Manager state after option 3
SELECT ps.current_step FROM conversation_states 
WHERE phone_number='+918882374849'
ORDER BY updated_at DESC LIMIT 1;

-- Driver state (new conversation started)
SELECT ps.phone_number, ps.current_step 
FROM conversation_states ps
WHERE phone_number='+818290323758'
ORDER BY created_at DESC LIMIT 1;
```

**Expected:**
- Manager: current_step = WAITING_MANAGER_REPLY (waiting for continuation)
- Driver: current_step = CONTACT_DRIVER (new conversation started)

---

### **STEP 4: Driver Investigation Flow**

#### Driver Confirms Vehicle: "1"

**Driver sends:** "1"

**Bot response:**
```
Thank you! Now please help us understand what happened.

Why did the vehicle stop?
1. Breakdown
2. Maintenance
3. Waiting Load
4. Leave
5. Other

Reply with: 1, 2, 3, 4, or 5
```

#### Database Check:
```sql
SELECT ps.current_step, ps.context_json 
FROM conversation_states ps
WHERE phone_number='+818290323758'
ORDER BY updated_at DESC LIMIT 1;
```

**Expected:**
- `current_step`: ASK_DRIVER_STOP_REASON
- `context_json`: Contains {reason_confirmed: true}

---

### **STEP 5: Collect Stop Reason**

#### Driver Selects Reason: "1" (Breakdown)

**Bot response:**
```
I see, the vehicle has broken down.

We will arrange for mechanical assistance.

Can you please share the current location of the vehicle?
For example: "Main Road, Noida, near Sector 18"
```

#### Database Check:
```sql
SELECT ps.current_step, ps.context_json 
FROM conversation_states ps
WHERE phone_number='+818290323758'
ORDER BY updated_at DESC LIMIT 1;
```

**Expected:**
- `current_step`: ASK_DRIVER_LOCATION
- `context_json`: {reason: "Breakdown", reason_confirmed: true}

---

### **STEP 6: Collect Location**

#### Driver Sends Location: "Sector 18, Noida, near petrol pump"

**Bot response:**
```
Thank you! Location recorded: Sector 18, Noida, near petrol pump

Do you need a mechanic?
Reply: 1 = Yes, 2 = No
```

#### Database Check:
```sql
SELECT ps.current_step, ps.context_json 
FROM conversation_states ps
WHERE phone_number='+818290323758'
ORDER BY updated_at DESC LIMIT 1;

-- Verify location stored in context
SELECT json_extract(context_json, '$.location') as driver_location 
FROM conversation_states 
WHERE phone_number='+818290323758'
ORDER BY updated_at DESC LIMIT 1;
```

**Expected:**
- `current_step`: ASK_NEED_MECHANIC
- Location saved in context_json

---

### **STEP 7: Mechanic Requirement**

#### Driver Replies: "1" (Yes, needs mechanic)

**Bot response:**
```
Understood. Mechanic assistance will be arranged.

How long do you expect the vehicle to be back on road?
Estimate in hours: e.g., "2", "3.5", "4"
```

#### Database Check:
```sql
SELECT ps.current_step, ps.context_json 
FROM conversation_states ps
WHERE phone_number='+818290323758'
ORDER BY updated_at DESC LIMIT 1;

-- Verify mechanic flag
SELECT json_extract(context_json, '$.needs_mechanic') as mechanic_needed 
FROM conversation_states 
WHERE phone_number='+818290323758'
ORDER BY updated_at DESC LIMIT 1;
```

**Expected:**
- `current_step`: ASK_EXPECTED_RESTART_TIME
- `needs_mechanic`: true

---

### **STEP 8: Expected Restart Time**

#### Driver Estimates: "2.5"

**Bot response:**
```
Thank you! Expected restart time: 2.5 hours

Generating investigation summary...
```

#### Investigation Summary Sent to Manager:
```
📋 **INVESTIGATION SUMMARY**

Vehicle: DL-01-AB-1234
Driver: Driver Amit
Location: Sector 18, Noida, near petrol pump
Time: 2024-01-15 14:45:30

**Issue Details:**
Stop Reason: Breakdown
Current Location: Sector 18, Noida, near petrol pump
Needs Mechanic: Yes
Expected Restart: 2.5 hours

[Summary sent to Manager for follow-up]
```

#### Database State:
```sql
-- Driver conversation completed
SELECT ps.current_step, ps.context_json 
FROM conversation_states ps
WHERE phone_number='+818290323758'
ORDER BY updated_at DESC LIMIT 1;

-- Check if summary stored in chat_messages
SELECT phone_number, bot_response FROM chat_messages
WHERE phone_number='+918290323758'
AND bot_response LIKE '%INVESTIGATION SUMMARY%'
ORDER BY created_at DESC LIMIT 1;
```

**Expected:**
- `current_step`: ASK_ISSUE_RESOLVED (manager follow-up state)

---

### **STEP 9: Follow-up Check (Manager)**

**System sends follow-up after ~1 hour:**
```
📞 Follow-up Check

Vehicle: DL-01-AB-1234
Expected Restart: 2.5 hours ago

Has the issue been resolved?
1. Yes, vehicle is back on road
2. No, still working on it
3. Escalate to support ticket

Reply with: 1, 2, or 3
```

#### Manager Replies: "1" (Yes, resolved)

**Bot response:**
```
Great! Issue resolved and vehicle is operational.

Alert Status: CLOSED ✓
```

#### Database Final State:
```sql
-- Alert marked as closed
SELECT id, status, alert_type, created_at, updated_at FROM alerts
WHERE vehicle_id IN (
    SELECT id FROM vehicles WHERE vehicle_number='DL-01-AB-1234'
)
ORDER BY created_at DESC LIMIT 1;

-- Final conversation states
SELECT phone_number, current_step FROM conversation_states 
WHERE phone_number IN ('+918882374849', '+818290323758')
ORDER BY updated_at DESC;

-- Complete chat history
SELECT phone_number, user_message, bot_response, created_at 
FROM chat_messages
WHERE phone_number IN ('+918882374849', '+818290323758')
ORDER BY created_at DESC LIMIT 20;
```

**Expected:**
- Alert status: CLOSED
- All conversation states: CLOSED
- Chat messages showing complete flow

---

## SQL Verification Queries

### Complete Workflow Verification
```sql
-- 1. Check alert creation and current status
SELECT 
    a.id as alert_id,
    v.vehicle_number,
    a.status,
    a.alert_type,
    u.name as manager_name,
    u.phone_number as manager_phone,
    a.created_at
FROM alerts a
JOIN vehicles v ON a.vehicle_id = v.id
JOIN users u ON v.manager_id = u.id
WHERE v.vehicle_number = 'DL-01-AB-1234'
ORDER BY a.created_at DESC LIMIT 1;

-- 2. Check manager conversation flow
SELECT 
    phone_number,
    current_step,
    context_json,
    created_at,
    updated_at
FROM conversation_states
WHERE phone_number = '+918882374849'
ORDER BY updated_at DESC;

-- 3. Check driver investigation details
SELECT 
    phone_number,
    current_step,
    context_json,
    created_at,
    updated_at
FROM conversation_states
WHERE phone_number = '+818290323758'
ORDER BY updated_at DESC;

-- 4. Check all messages exchanged
SELECT 
    phone_number,
    user_message,
    bot_response,
    created_at
FROM chat_messages
WHERE phone_number IN ('+918882374849', '+818290323758')
ORDER BY created_at DESC LIMIT 30;

-- 5. Check vehicle status at each stage
SELECT 
    v.vehicle_number,
    vs.ign_state,
    vs.mode,
    vs.location,
    vs.last_gps_time,
    vs.updated_at
FROM vehicles v
JOIN vehicle_status vs ON v.id = vs.vehicle_id
WHERE v.vehicle_number = 'DL-01-AB-1234';
```

---

## State Transitions Reference

```
FLEET_ALERT_CREATED (Manager receives alert)
    ↓
    ├─→ [Reply: 1] → CONTACT_DRIVER (Handle it)
    │       ↓
    │       Driver receives alert
    │       ↓
    │   CONTACT_DRIVER (Driver confirms vehicle)
    │       ↓
    │   ASK_DRIVER_STOP_REASON (Why stopped?)
    │       ↓
    │   ASK_DRIVER_LOCATION (Where are you?)
    │       ↓
    │   ASK_NEED_MECHANIC (Need mechanic?)
    │       ↓
    │   ASK_EXPECTED_RESTART_TIME (When ready?)
    │       ↓
    │   [Investigation Summary Generated]
    │       ↓
    │   ASK_ISSUE_RESOLVED (Follow-up to manager)
    │       ↓
    │   CLOSED (Alert resolved)
    │
    ├─→ [Reply: 2] → WAITING_NEW_CONTACT_NAME (Transfer)
    │       ↓
    │   WAITING_NEW_CONTACT_PHONE
    │       ↓
    │   [New contact gets FLEET_ALERT_CREATED]
    │
    └─→ [Reply: 3] → WAITING_MANAGER_REPLY (Contact driver)
            ↓
            [Same as Reply: 1 flow above]
```

---

## Common Test Scenarios

### Scenario 1: Quick Resolution
```
Manager: "1" → Driver: "1" (confirm) → "1" (Breakdown) → "location" 
→ "1" (needs mechanic) → "1" (1 hour) 
→ Manager: "1" (resolved) → CLOSED ✓
```

### Scenario 2: Transfer Chain
```
Manager 1: "2" → Transfer to Manager 2 → Manager 2: "1" 
→ Driver investigation flow → CLOSED ✓
```

### Scenario 3: Escalation
```
Driver investigation → Manager: "3" (Create support ticket)
→ Ticket created in db → Driver needs on-site support
```

### Scenario 4: Long Delay
```
Manager: "1" → Driver: "1" → "1" (Maintenance) → "location" 
→ "1" (needs mechanic) → "4" (4 hours expected)
→ Follow-up after 4 hours → "2" (Still working)
→ Re-escalate to support ticket
```

---

## Debugging Commands

### Reset Test Data
```bash
# Clear and re-seed
python scripts/seed_dummy_data.py
```

### Check Scheduler Status
```python
# In app/main.py
from scheduler.vehicle_monitor import start_scheduler, get_scheduler
scheduler = get_scheduler()
print(scheduler.get_jobs())
```

### Manual Alert Detection
```python
# Test alert creation
from app.services.alert_service import detect_alerts
from app.db.database import SessionLocal

db = SessionLocal()
alerts = detect_alerts(db=db)
print(f"Created {len(alerts)} alerts")
db.close()
```

### Send Test Message
```python
# Test conversation handler
from app.api.webhook import handle_support_message
from app.db.models import User
from app.db.database import SessionLocal

db = SessionLocal()
user = db.query(User).filter_by(phone_number="+918882374849").first()
response = handle_support_message(user, "1", db=db)
print(f"Response: {response}")
db.close()
```

---

## Expected Database Schema

### Key Tables and Relationships

```
users (id, name, phone_number, role, created_at)
    ↓
vehicles (id, vehicle_number, manager_id, driver_id, created_at)
    ├─ manager_id → users.id
    ├─ driver_id → users.id
    └─ vehicle_status (vehicle_id, ign_state, mode, location, last_gps_time)
    
alerts (id, vehicle_id, status, alert_type, created_at, updated_at)
    └─ vehicle_id → vehicles.id

conversation_states (id, phone_number, current_step, context_json, created_at, updated_at)
    └─ phone_number → users.phone_number (indexed)

chat_messages (id, phone_number, user_message, bot_response, created_at)
    └─ phone_number → users.phone_number

problems (id, title, description, severity, machine_model, created_at)
solutions (id, problem_id, step_number, description, created_at)
    └─ problem_id → problems.id
```

---

## Troubleshooting

### Issue: Alert not created
- Check: Vehicle status has ign_state='off' AND mode='not working'
- Check: Scheduler is running (`python scripts/seed_dummy_data.py` runs detect_alerts)

### Issue: Manager doesn't receive message
- Check: Manager phone number is valid (starts with +)
- Check: WhatsApp API credentials are correct
- Check: CORS origin is added for WhatsApp webhook

### Issue: State transition error
- Check: Previous state is in allowed transitions
- Check: `context_json` has required fields
- Check: Phone number format matches

### Issue: Summary not generated
- Check: Groq API key is set in .env
- Check: Problem/Solution records exist in database

---

## Next Steps After Testing

1. ✅ Verify all state transitions work correctly
2. ✅ Check WhatsApp messages are formatted properly
3. ✅ Validate investigation summary generation
4. ✅ Test alert closure and reopening
5. ✅ Monitor scheduler for periodic vehicle checks
6. ✅ Deploy to production with real vehicle data


---

## 💾 Database Schema

### Vehicles Table
- vehicle_number
- manager_id
- driver_id
- status (relationship)

### Vehicle Status
- ign_state (off/on)
- mode (working/not working)
- location
- last_gps_time

### Alerts Table
- vehicle_id
- status (OPEN/CLOSED)
- alert_type (VEHICLE_OFF_NOT_WORKING)
- created_at

### Conversation States
- phone_number
- current_step (state machine)
- context_json (troubleshooting data, LED status, etc.)

---

## 🔧 State Transitions Map

```
Scheduler Detection
     ↓
FLEET_ALERT_CREATED (Manager receives alert)
     ↓
Manager chooses option 3
     ↓
CONTACT_DRIVER (Driver receives alert)
     ↓
Driver responds
     ↓
ASK_IF_DRIVING (Is driver currently driving?)
     ↓
├─ Yes → ASK_CAN_PARK (Can park for 30 mins?)
│        ├─ Yes → ASK_TURN_ON_IGNITION
│        └─ No → WAITING_MANAGER_REPLY
│
└─ No → ASK_TURN_ON_IGNITION (Turn on ignition)
        ↓
        TROUBLESHOOT_POWER_LED
        ├─ OFF → ESCALATION_SUPPORT_TICKET
        └─ OK → TROUBLESHOOT_GSM_LED
                ├─ OFF → ESCALATION_SUPPORT_TICKET
                └─ OK → TROUBLESHOOT_GPS_LED
                        ├─ OFF → ESCALATION_SUPPORT_TICKET
                        └─ OK → ASK_RESOLUTION_CONFIRMATION
                                ├─ Yes → SUMMARY_SENT
                                └─ No → ESCALATION_SUPPORT_TICKET
```

---

## ✅ Features Implemented

- ✓ 1-minute automated vehicle monitoring
- ✓ Automatic alert creation for "NOT WORKING" vehicles
- ✓ Manager notification workflow
- ✓ Driver contact & verification
- ✓ Guided troubleshooting (Power → GSM → GPS LEDs)
- ✓ Live API verification support
- ✓ Resolution confirmation
- ✓ Automatic escalation
- ✓ Complete conversation state machine
- ✓ WhatsApp integration at all steps

---

## 🧪 Testing Commands

All test commands available in this document can be run with:
```bash
curl -X POST http://127.0.0.1:8000/webhook/ \
  -H "Content-Type: application/json" \
  -d '{payload}'
```

Or use PowerShell:
```powershell
$json = '{payload}'
$response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/webhook/" `
  -Method POST -Body $json -ContentType "application/json" -UseBasicParsing
$response
```
