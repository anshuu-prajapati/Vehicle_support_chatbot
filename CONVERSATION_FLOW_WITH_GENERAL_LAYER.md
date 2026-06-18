# Complete Conversation Flow with General Layer

**Visual representation of the conversation flow including the new General Conversation Layer**

---

## 📊 Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    User Sends Message                            │
└─────────────────────────────────────┬───────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Reset Command Check                           │
│              ("reset", "restart", "cancel")                      │
└─────────────────────────────────────┬───────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
              YES   ▼                                   ▼  NO
          ┌─────────────────┐                    Continue
          │  Clear State    │
          │  Send Reset Msg │
          └─────────────────┘
                    │
                    ▼
          ┌─────────────────────────────────────────────────────┐
          │   🆕 GENERAL CONVERSATION LAYER (Task 6)            │
          │                                                     │
          │   Is this a general question/greeting/clarification?│
          │   - "Tum kon ho?"                                  │
          │   - "Kyu message kiya?"                           │
          │   - "Hello"                                        │
          │   - "Thank you"                                    │
          │   - "Kis company se ho?"                          │
          │   - "Kaunsi vehicle?"                             │
          └─────────────────┬───────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
        YES   ▼                           ▼  NO
    ┌──────────────────────┐      ┌────────────────────┐
    │ Answer Question      │      │ Continue with      │
    │ Maintain State       │      │ Normal Flow        │
    │ Return Pending Q     │      │                    │
    └──────────────────────┘      └─────────┬──────────┘
              │                             │
              │                             ▼
              │               ┌─────────────────────────────┐
              │               │  Initial Selection          │
              │               │  (No active state)          │
              │               └──────────────┬──────────────┘
              │                              │
              │                ┌─────────────┴─────────────┐
              │                │                           │
              │          Numeric (1-8)              Natural Language
              │                │                           │
              │                ▼                           ▼
              │       ┌──────────────────┐    ┌──────────────────────┐
              │       │ Direct Mapping   │    │ "Don't Know" Check   │
              │       │ 1→WORKSHOP       │    │ (Task 5)             │
              │       │ 2→ACCIDENT       │    └──────────┬───────────┘
              │       │ 3→BATTERY        │               │
              │       │ 4→GPS_REMOVED    │    ┌──────────┴──────────┐
              │       │ 5→GPS_DAMAGED    │    │                     │
              │       │ 6→VEHICLE_RUNNING│  YES│                   NO│
              │       │ 7→VEHICLE_STANDING│   ▼                     ▼
              │       │ 8→OTHER          │ Clarification      LLM Classification
              │       └──────────┬───────┘ Mode                     │
              │                  │         │                        │
              │                  │         │          ┌─────────────┴──────────┐
              │                  │         │          │                        │
              │                  │         │      CONFIDENT                 UNKNOWN
              │                  │         │          │                        │
              │                  └─────────┴──────────┴────────────────────────┤
              │                                    │                           │
              │                                    ▼                           ▼
              │                      ┌──────────────────────────┐    ┌──────────────────┐
              │                      │   Route to Flow          │    │ OTHER Flow       │
              │                      └──────────┬───────────────┘    │ (Task 4)         │
              │                                 │                    │ AI Clarification │
              │                                 │                    └──────────────────┘
              │                                 │
              │                                 ▼
              │               ┌──────────────────────────────────────────────┐
              │               │          FLOW ROUTING                        │
              │               └──────────────────────────────────────────────┘
              │                                 │
              │         ┌───────────────────────┼───────────────────────┐
              │         │                       │                       │
              │         ▼                       ▼                       ▼
              │   ┌─────────┐           ┌─────────────┐         ┌──────────┐
              │   │WORKSHOP │           │  ACCIDENT   │         │ BATTERY  │
              │   │(Task 3) │           │             │         │(Task 3)  │
              │   └────┬────┘           └──────┬──────┘         └────┬─────┘
              │        │                       │                     │
              │        │   Ask Expected Date   │  Ask Workshop       │  Ask Expected Date
              │        │   Close Case          │  Status             │  Close Case
              │        │                       │  Create Ticket      │
              │        │                       │                     │
              │        │         ┌─────────────┼─────────────────────┤
              │        │         │             │                     │
              │        │         ▼             ▼                     ▼
              │        │   ┌──────────┐  ┌──────────────┐    ┌────────────┐
              │        │   │GPS_REMOVED│  │GPS_DAMAGED   │    │VEHICLE_    │
              │        │   │           │  │(Task 2)      │    │RUNNING     │
              │        │   └─────┬─────┘  └──────┬───────┘    └─────┬──────┘
              │        │         │               │                   │
              │        │         │  Ask Date     │  Ask Location     │  Ask Location
              │        │         │  Service Req  │  Service Req      │  Service Req
              │        │         │               │                   │
              │        │         │               │                   │
              │        │         ├───────────────┴───────────────────┤
              │        │         │                                   │
              │        │         ▼                                   ▼
              │        │   ┌──────────────┐              ┌────────────────────┐
              │        │   │VEHICLE_      │              │ OTHER              │
              │        │   │STANDING      │              │ (Task 4)           │
              │        │   │(Task 1)      │              │ AI Clarification   │
              │        │   └──────┬───────┘              └─────────┬──────────┘
              │        │          │                                │
              │        │          │  48h Check                     │  4 Paths:
              │        │          │  <48h: Service                 │  1. Reclassify
              │        │          │  >=48h: Close                  │  2. GPS Tech
              │        │          │                                │  3. Non-GPS
              │        │          │                                │  4. Fallback
              │        │          │                                │
              │        └──────────┴────────────────────────────────┘
              │                             │
              │                             ▼
              │               ┌─────────────────────────────┐
              │               │  Service Request Collection │
              │               │  - Location                 │
              │               │  - Date/Time               │
              │               │  - Contact                 │
              │               │  - Create Ticket           │
              │               └─────────────┬───────────────┘
              │                             │
              │                             ▼
              │               ┌─────────────────────────────┐
              │               │  Engineer Assignment        │
              │               │  - Assign nearest           │
              │               │  - Status: ASSIGNED         │
              │               └─────────────┬───────────────┘
              │                             │
              │                             ▼
              │               ┌─────────────────────────────┐
              │               │  Clear State                │
              │               │  End Conversation           │
              │               └─────────────────────────────┘
              │
              └──────────────────────────────────────────────┘
                            END
```

---

## 🔄 General Conversation Layer Flow (Task 6)

```
User Message
     │
     ▼
┌─────────────────────────────────┐
│ is_general_conversation()?      │
└────────┬───────────────┬────────┘
         │               │
     YES │               │ NO
         │               │
         ▼               └──────────────────────────────┐
┌─────────────────────────────────┐                    │
│ get_conversation_type()         │                    │
│                                 │                    │
│ IDENTITY    - "Tum kon ho?"    │                    │
│ WHY_CONTACT - "Kyu message?"   │                    │
│ COMPANY     - "Kis company?"   │                    │
│ VEHICLE     - "Kaunsi vehicle?"│                    │
│ PROBLEM     - "Kya hua?"       │                    │
│ CONFUSION   - "Samajh nahi"    │                    │
│ AUTOMATED   - "Bot hai kya?"   │                    │
│ GREETING    - "Hello"          │                    │
│ THANKS      - "Thank you"      │                    │
│ HELP        - "Help me"        │                    │
│ ACKNOWLEDGMT- "Ok", "Achha"    │                    │
└────────────────┬────────────────┘                    │
                 │                                     │
                 ▼                                     │
┌─────────────────────────────────┐                    │
│ get_pending_question()          │                    │
│ - Based on current_step         │                    │
│ - Based on context              │                    │
└────────────────┬────────────────┘                    │
                 │                                     │
                 ▼                                     │
┌─────────────────────────────────┐                    │
│ generate_general_response()     │                    │
│ - Context-aware                 │                    │
│ - Includes vehicle info         │                    │
│ - Includes pending question     │                    │
└────────────────┬────────────────┘                    │
                 │                                     │
                 ▼                                     │
┌─────────────────────────────────┐                    │
│ Return (True, response)         │                    │
│ State: UNCHANGED                │                    │
└─────────────────────────────────┘                    │
                                                       │
                                                       ▼
                                        ┌──────────────────────────┐
                                        │ Return (False, None)     │
                                        │ Continue Normal Flow     │
                                        └──────────────────────────┘
```

---

## 📝 Example Flow Walkthroughs

### Walkthrough 1: Identity Question During GPS Damaged Flow

```
State: GPS_DAMAGED_LOCATION (waiting for location)
Context: {"gps_damaged_sub_step": "GPS_DAMAGED_LOCATION"}

User: "Tum kon ho?"
  │
  ▼
General Conversation Layer
  │
  ├─ is_general_conversation("Tum kon ho?") → TRUE
  ├─ get_conversation_type() → IDENTITY
  ├─ get_pending_question(GPS_DAMAGED_LOCATION) → "Kripya vehicle ki current location..."
  └─ generate_general_response()
  
Bot: "Main GPS Support Assistant hoon. 😊
      
      Humein vehicle MH12AB1234 se GPS data receive nahi ho raha hai,
      isliye hum issue samajhne ki koshish kar rahe hain.
      
      Kripya vehicle ki current location bata dijiye jahan inspection
      karwana hai."

State After: GPS_DAMAGED_LOCATION (UNCHANGED)
Context After: (UNCHANGED)
```

### Walkthrough 2: Issue Description

```
State: None (initial selection)

User: "GPS toot gaya hai"
  │
  ▼
General Conversation Layer
  │
  └─ is_general_conversation("GPS toot gaya hai") → FALSE
  
Continue Normal Flow
  │
  ▼
LLM Classification
  │
  └─ classify_customer_intent() → GPS_DAMAGED
  
Route to GPS Damaged Flow
  │
  ▼
Bot: "Dhanyavaad. 🙏
      
      Humne note kar liya hai ki GPS device damage ho gaya hai.
      
      Kripya vehicle ki current location bata dijiye jahan inspection
      karwana hai."

State After: GPS_DAMAGED_LOCATION
Context: {"issue_classification": "GPS_DAMAGED", "gps_damaged_sub_step": "GPS_DAMAGED_LOCATION"}
```

### Walkthrough 3: Thank You During Workshop Flow

```
State: WORKSHOP_CONFIRMATION (waiting for expected date)

User: "Thank you"
  │
  ▼
General Conversation Layer
  │
  ├─ is_general_conversation("Thank you") → TRUE
  ├─ get_conversation_type() → THANKS
  ├─ get_pending_question(WORKSHOP_CONFIRMATION) → "Vehicle ke dobara operational..."
  └─ generate_general_response()
  
Bot: "Aapka swagat hai. 😊
      
      Vehicle ke dobara operational hone ki expected date kya hai?"

State After: WORKSHOP_CONFIRMATION (UNCHANGED)
```

---

## 🎯 Key Integration Points

### 1. Entry Point
**File**: `app/services/service_engineer_flow_service.py`  
**Function**: `_handle_service_engineer_message_internal()`  
**Lines**: 457-483

```python
# === GENERAL CONVERSATION LAYER ===
is_general, general_response = handle_general_conversation(
    text=text_body,
    current_step=state.current_step if state else None,
    context=context,
    vehicle_number=vehicle_number,
    last_location=last_location
)

if is_general:
    # Return general response WITHOUT changing conversation state
    return general_response

# === END GENERAL CONVERSATION LAYER ===
```

### 2. Position in Flow
- ✅ **After** reset command check
- ✅ **Before** initial status selection
- ✅ **Before** greeting check
- ✅ **Before** issue classification
- ✅ **Before** flow routing

This ensures general conversation is detected FIRST before any state changes.

---

## 🔍 Detection Logic

### What IS General Conversation?
```python
✅ "Tum kon ho?"           → IDENTITY
✅ "Kyu message kiya?"     → WHY_CONTACT
✅ "Kis company se ho?"    → COMPANY
✅ "Kaunsi vehicle?"       → VEHICLE
✅ "Hello"                 → GREETING
✅ "Thank you"             → THANKS
✅ "Samajh nahi aaya"      → CONFUSION
✅ "Bot hai kya?"          → AUTOMATED
✅ "ok", "achha"           → ACKNOWLEDGMENT
```

### What is NOT General Conversation?
```python
❌ "GPS toot gaya hai"           → Issue Description
❌ "Vehicle workshop mein hai"   → Status Update
❌ "Battery nikali hui hai"      → Status Update
❌ "2 din se khadi hai"          → Duration Response
❌ "Kirti Nagar Delhi"           → Location Response
❌ "Haan service chahiye"        → Service Confirmation
```

### Smart Exclusion
```python
# Status keywords with 2+ words → NOT general
"vehicle workshop mein"     → NOT general (status update)
"GPS toot gaya"            → NOT general (issue description)

# Exception: Identity/Why keywords win
"GPS workshop mein kon ho"  → IS general (identity question)
"Battery nikali kyu"        → IS general (why question)
```

---

## ✅ Checklist for Task 6

- [x] Created general conversation handler module
- [x] Implemented detection logic with smart exclusion
- [x] Implemented 11 conversation types
- [x] Implemented context-aware response generation
- [x] Implemented pending question retrieval
- [x] Integrated in service engineer flow
- [x] Positioned before issue classification
- [x] Preserves conversation state
- [x] Returns to pending question
- [x] Includes vehicle context
- [x] Tested with multiple scenarios
- [x] Documented completely

---

## 🎉 Result

The General Conversation Layer successfully intercepts and handles:
- Identity questions
- Clarification requests
- Greetings and farewells
- Thanks and acknowledgments
- Help requests
- Confusion statements

All while:
- ✅ Maintaining conversation state
- ✅ Providing context-aware responses
- ✅ Returning to pending questions
- ✅ Behaving like a real support executive

**Status**: ✅ COMPLETE AND PRODUCTION READY

---

**Created**: June 18, 2026  
**Task 6**: General Conversation Layer Implementation
