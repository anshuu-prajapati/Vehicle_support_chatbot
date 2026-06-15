# GPS Service Engineer Flow - Complete Flow Diagram

## Visual Flow Representation

```
                           📱 START
                              │
                    ┌─────────┴─────────┐
                    │  GPS ALERT SENT   │
                    │  Vehicle Offline  │
                    └─────────┬─────────┘
                              │
                              ↓
                    ┌─────────────────────┐
                    │ User Presses "1"    │
                    │ (AI Assistance)     │
                    └─────────┬───────────┘
                              │
                              ↓
        ┌─────────────────────────────────────────────┐
        │ Q1 (Implicit): Kya yeh vehicle aapki hai?  │
        │ Q2: Where is vehicle? Why inactive?        │
        └─────────────────┬───────────────────────────┘
                          │
                          ↓
            ┌─────────────────────────┐
            │ INTENT CLASSIFICATION   │
            │ (AI analyzes response)  │
            └──────────┬──────────────┘
                       │
        ┌──────────────┼──────────────────────────┐
        │              │                          │
        ↓              ↓                          ↓
┌───────────┐  ┌──────────────┐         ┌───────────────┐
│ WORKSHOP  │  │   ACCIDENT   │   ...   │ GPS_DAMAGED   │ ← YOUR CASE
└─────┬─────┘  └──────┬───────┘         └───────┬───────┘
      │               │                         │
      ↓               ↓                         ↓


═══════════════════════════════════════════════════════════
                    YOUR CASE: GPS DAMAGED
═══════════════════════════════════════════════════════════

User: "delhi gps khrab ho gya"
          ↓
    ┌──────────────────┐
    │ GPS_DAMAGED Flow │
    └────────┬─────────┘
             │
             ↓
    ┌────────────────────────┐
    │ Get Location           │
    │ "Current location?"    │
    └────────┬───────────────┘
             │
    User: "delhi, kirti nagar"
             │
             ↓
    ┌────────────────────────────────┐
    │ Q12: GPS physically damaged?   │
    │ 1️⃣ हाँ / Yes                   │
    │ 2️⃣ नहीं / No                   │
    └────────┬───────────────────────┘
             │
    ┌────────┴────────┐
    │                 │
    ↓ YES             ↓ NO
    │              ┌──────────┐
    │              │ CLOSE    │
    │              │ CASE     │
    │              └──────────┘
    ↓
┌──────────────────────────────┐
│ Q13: Replacement needed?     │
│ 1️⃣ हाँ / Yes                 │
│ 2️⃣ नहीं / No                 │
└────────┬─────────────────────┘
         │
    ┌────┴────┐
    │         │
    ↓ YES     ↓ NO
    │      ┌──────────┐
    │      │ CLOSE    │
    │      │ CASE     │
    │      └──────────┘
    ↓
┌─────────────────────────┐
│ SERVICE REQUEST         │
│ Start Data Collection   │
└───────┬─────────────────┘
        │
        ↓


═══════════════════════════════════════════════════════════
              SERVICE REQUEST DATA COLLECTION
              (Common for all flows leading here)
═══════════════════════════════════════════════════════════

        ┌────────────────────────┐
        │ Q25: Vehicle Number    │ ← Auto-filled if available
        └──────────┬─────────────┘
                   │
                   ↓
        ┌────────────────────────┐
        │ Q26: Owner Name        │ ← Auto-filled if available
        └──────────┬─────────────┘
                   │
                   ↓
        ┌────────────────────────┐
        │ Q27: Owner Mobile      │ ← Auto-filled if available
        └──────────┬─────────────┘
                   │
                   ↓
        ┌────────────────────────┐
        │ Q28: Current Location  │ ← Already collected for GPS_DAMAGED
        └──────────┬─────────────┘
                   │
                   ↓
        ┌────────────────────────┐
        │ Q29: Driver Name       │
        └──────────┬─────────────┘
                   │
                   ↓
        ┌────────────────────────┐
        │ Q30: Driver Mobile     │
        └──────────┬─────────────┘
                   │
                   ↓
        ┌────────────────────────┐
        │ Q31: Vehicle Available?│
        │ 1️⃣ हाँ  2️⃣ नहीं        │
        └──────────┬─────────────┘
                   │
                   ↓
        ┌────────────────────────┐
        │ Q32: Preferred Visit   │
        │      Date (DD/MM/YYYY) │
        └──────────┬─────────────┘
                   │
                   ↓
        ┌────────────────────────┐
        │ Q33: Preferred Visit   │
        │      Time (HH:MM)      │
        └──────────┬─────────────┘
                   │
                   ↓
        ┌────────────────────────┐
        │ Q34: Issue Type        │
        │ 1. GPS Not Working     │
        │ 2. GPS Removed         │
        │ 3. GPS Damaged         │ ← Pre-select for your case
        │ 4. Battery Related     │
        │ 5. GPS Reinstallation  │
        │ 6. Accident Related    │
        │ 7. Other               │
        └──────────┬─────────────┘
                   │
                   ↓
        ┌─────────────────────────────┐
        │ SHOW SUMMARY                │
        │                             │
        │ 📋 सर्विस रिक्वेस्ट सारांश  │
        │ 🚗 Vehicle: MH12AB1234      │
        │ 👤 Owner: Anshu Kumar       │
        │ 📞 Mobile: +919876543210    │
        │ 📍 Location: delhi, kirti..│
        │ 👨‍✈️ Driver: Ramesh           │
        │ 📅 Date: 16/06/2026         │
        │ 🕐 Time: 10:00 AM           │
        │ 🔧 Issue: GPS Damaged       │
        └──────────┬──────────────────┘
                   │
                   ↓
        ┌──────────────────────────────┐
        │ Q35: Assign Engineer?        │
        │ 1️⃣ हाँ / Yes                 │
        │ 2️⃣ नहीं / No                 │
        └──────────┬───────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ↓ YES                 ↓ NO
┌───────────────────┐  ┌──────────────────┐
│ CREATE TICKET     │  │ CREATE TICKET    │
│ Status: ASSIGNED  │  │ Status: ON_HOLD  │
│ Assign Engineer   │  │ No Engineer Yet  │
│ Send Notification │  │                  │
└────────┬──────────┘  └────────┬─────────┘
         │                      │
         └──────────┬───────────┘
                    ↓
        ┌───────────────────────────┐
        │ ✅ CONFIRMATION MESSAGE   │
        │                           │
        │ 🎫 Ticket: TKT-1234       │
        │ Engineer will contact you │
        │ Thank you!                │
        └───────────┬───────────────┘
                    │
                    ↓
        ┌───────────────────────────┐
        │ CLEAR CONVERSATION STATE  │
        │ Ready for next interaction│
        └───────────────────────────┘
                    │
                    ↓
                   END


═══════════════════════════════════════════════════════════
                    ALL 8 FLOW PATHS
═══════════════════════════════════════════════════════════

1. WORKSHOP FLOW
   User: "vehicle workshop mein hai"
   → Q3: Workshop for repair?
     → YES: Close Case
     → NO: Manual Verification

2. ACCIDENT FLOW
   User: "accident ho gaya"
   → Q5: GPS damaged in accident?
     → YES: Service Request (Q25-Q35)
     → NO: Close Case

3. BATTERY DISCONNECT FLOW
   User: "battery disconnect hai"
   → Q6: Maintenance disconnect?
     → YES: Q7: Reinstall needed?
       → YES: Service Request
       → NO: Close Case
     → NO: Q8: GPS data not coming?
       → YES: Service Request
       → NO: Close Case

4. GPS REMOVED FLOW
   User: "gps nikaal diya"
   → Q10: Who removed? (Customer/Workshop/Unknown)
   → Q11: Reinstall?
     → YES: Service Request (Q25-Q35)
     → NO: Close Case

5. GPS DAMAGED FLOW ← YOUR CASE
   User: "gps khrab ho gya"
   → Get Location
   → Q12: Physically damaged?
     → YES: Q13: Replacement needed?
       → YES: Service Request (Q25-Q35)
       → NO: Close Case
     → NO: Close Case

6. VEHICLE STANDING FLOW
   User: "vehicle khadi hai"
   → Q14: How long standing?
     → >48hrs: Q15: Inspection needed?
       → YES: Service Request
       → NO: Close Case
     → <48hrs: Q16: GPS data coming?
       → YES: Close Case
       → NO: Service Request

7. VEHICLE RUNNING FLOW
   User: "vehicle chal rahi hai lekin gps nahi"
   → Q18: Driver name?
   → Q19: Driver mobile?
   → Q20: Current location?
   → Q21: Available for inspection?
     → YES: Service Request (Q25-Q35)
     → NO: Q22: When available?
       → Service Request (Q25-Q35)

8. OTHER/UNKNOWN FLOW
   User: "kuch aur problem hai"
   → Q23: Describe issue
   → Q24: GPS related?
     → YES: Service Request (Q25-Q35)
     → NO: Close Case


═══════════════════════════════════════════════════════════
                    CODE STRUCTURE
═══════════════════════════════════════════════════════════

app/services/
│
├── service_engineer_flow_service.py
│   ├── handle_service_engineer_message()  ← Main Entry
│   ├── send_initial_customer_message()    ← Q1
│   ├── handle_intent_classification()     ← Q2
│   ├── _route_to_flow_handler()           ← Router
│   └── handle_engineer_assignment()       ← Q35
│
├── flow_handlers/
│   ├── __init__.py
│   ├── workshop_flow.py              ← Q3-Q4
│   ├── accident_flow.py              ← Q5
│   ├── battery_flow.py               ← Q6-Q8
│   ├── gps_removed_flow.py           ← Q10-Q11
│   ├── gps_damaged_flow.py           ← Q12-Q13 ← YOUR CASE
│   ├── vehicle_standing_flow.py      ← Q14-Q16
│   ├── vehicle_running_flow.py       ← Q17-Q22
│   ├── other_issue_flow.py           ← Q23-Q24
│   └── service_request_collector.py  ← Q25-Q34
│
├── state_manager.py
│   └── ConversationStep (Enum with all states)
│
└── ticket_service.py
    ├── create_service_request_ticket()
    ├── update_ticket()
    └── assign_engineer()


═══════════════════════════════════════════════════════════
                    STATE TRANSITIONS
                    (Your specific case)
═══════════════════════════════════════════════════════════

MAIN_MENU
    ↓ (User: "1")
INTENT_CLASSIFICATION
    ↓ (User: "delhi gps khrab ho gya")
GPS_DAMAGED_LOCATION
    ↓ (User: "delhi, kirti nagar")
GPS_DAMAGED_PHYSICAL_DAMAGE (Q12)
    ↓ (User: "1" - Yes)
GPS_DAMAGED_REPLACEMENT_NEEDED (Q13)
    ↓ (User: "1" - Yes)
DATA_COLLECTION_VEHICLE_NUMBER (Q25)
    ↓
DATA_COLLECTION_OWNER_NAME (Q26)
    ↓
DATA_COLLECTION_OWNER_MOBILE (Q27)
    ↓
DATA_COLLECTION_LOCATION (Q28)
    ↓
DATA_COLLECTION_DRIVER_NAME (Q29)
    ↓
DATA_COLLECTION_DRIVER_MOBILE (Q30)
    ↓
DATA_COLLECTION_VEHICLE_AVAILABLE (Q31)
    ↓
DATA_COLLECTION_VISIT_DATE (Q32)
    ↓
DATA_COLLECTION_VISIT_TIME (Q33)
    ↓
DATA_COLLECTION_ISSUE_TYPE (Q34)
    ↓
ENGINEER_ASSIGNMENT (Q35)
    ↓ (User: "1" - Yes)
MAIN_MENU (cleared)
    ↓
Ticket Created ✅
Engineer Assigned ✅
Notification Sent ✅


═══════════════════════════════════════════════════════════
                    SUCCESS!
═══════════════════════════════════════════════════════════

✅ All 8 flows implemented
✅ Service request collector working
✅ Engineer assignment functional
✅ Your specific issue FIXED
✅ Ready for production
```

## Quick Reference

### Your Conversation Path:
1. Alert → "1" → Q2 → GPS_DAMAGED
2. Location → Q12 → Q13
3. Q25-Q34 → Q35
4. Ticket Created ✅

### Key Files for Your Case:
- `gps_damaged_flow.py` - Handles Q12-Q13
- `service_request_collector.py` - Handles Q25-Q34
- `service_engineer_flow_service.py` - Orchestrates everything

### Test Command:
Send: "1" → "delhi gps khrab ho gya" → "delhi, kirti nagar" → "1" → "1" → [answer Q25-Q34] → "1"

Result: ✅ Complete ticket with engineer assigned!
