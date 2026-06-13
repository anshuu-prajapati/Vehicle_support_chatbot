# Vehicle Support Chatbot - Conversation Flow Tree

This document describes the complete conversation flow tree for the Vehicle Support Chatbot system, showing all possible paths and decision points.

## 📋 Overview

The chatbot supports two main entry points:
1. **Proactive Alerts**: System sends breakdown alerts to managers
2. **User-Initiated**: Users start conversation with greetings

---

## 🌳 Complete Flow Tree

### 1. ENTRY POINTS

```
┌─────────────────────────────────────────────┐
│                ENTRY POINTS                 │
├─────────────────────────────────────────────┤
│ A) Proactive Alert (Breakdown API)          │
│ B) User Greeting (Hi, Hello, Namaste)      │
└─────────────────────────────────────────────┘
```

---

### 2. PATH A: PROACTIVE BREAKDOWN ALERT

#### A1. Breakdown Alert Message
```
🚨 VEHICLE ALERT 🚨
Vehicle [NUMBER] has technical issues:
- GPS is not working
- Data transmission has stopped
Location: [LOCATION]
Last GPS: [TIME]

1️⃣ Press 1 for AI assistance
```

#### A2. User Response to Alert
```
User presses "1" → Go to A3 (Company Manager Check)
```

#### A3. Company Manager Verification
```
┌─────────────────────────────────────────────┐
│ Are we talking to the manager of [COMPANY]? │
│ 1️⃣ हाँ / Yes                               │
│ 2️⃣ नहीं / No                                │
└─────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
    [A4: YES]                  [A5: NO]
```

#### A4. Manager Says YES - Continue or Delegate
```
┌─────────────────────────────────────────────┐
│ Should we continue with you or talk with    │
│ somebody else?                              │
│ 1️⃣ Continue with me                        │
│ 2️⃣ Talk with someone else                  │
└─────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
   [A6: GPS Repair]           [A7: Contact Selection]
```

#### A5. Manager Says NO - Wrong Person
```
┌─────────────────────────────────────────────┐
│ Please provide the phone number of the      │
│ right person we should talk to              │
│ Example: 9876543210                         │
└─────────────────────────────────────────────┘
         │
         ▼
   [A10: Send Alert to Contact] → [End]
```

#### A6. Continue with Manager - GPS Repair Flow
```
┌─────────────────────────────────────────────┐
│ GPS system repair needed.                   │
│ Are you near the vehicle?                   │
│ 1️⃣ हाँ / Yes                               │
│ 2️⃣ नहीं / No                                │
└─────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
   [A8: Near Vehicle]         [A9: Not Near Vehicle]
```

#### A7. Talk with Someone Else - Contact Selection
```
┌─────────────────────────────────────────────┐
│ Should we contact supervisor or driver?     │
│ 1️⃣ सुपरवाइजर / Supervisor                  │
│ 2️⃣ ड्राइवर / Driver whose number is [DB]   │
└─────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
   [Supervisor Path]           [Driver Path]
```

**Supervisor Path:**
```
Ask for supervisor number → Send alert to supervisor → [A6: GPS Repair Flow]
```

**Driver Path:**
```
Use database driver number → Send alert to driver → [A6: GPS Repair Flow]
(If no DB number: Ask for manual input)
```

#### A8. Near Vehicle - Ignition Fix with Automatic Verification
```
┌─────────────────────────────────────────────┐
│ Great! Turn on the vehicle ignition         │
│ Press '1' after turning on ignition        │
│ 1️⃣ इग्निशन ऑन कर दिया                     │
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│ 🔍 GPS Verification (Automatic)             │
│ • Wait 10 seconds for GPS stabilization     │
│ • Check vehicle status via GET API          │
│ • Provide intelligent feedback              │
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│ Three Possible Outcomes:                    │
│                                             │
│ ✅ GPS Working: "GPS is updating! 🎉"      │
│ ⚠️  Ignition Off: "Please turn on ignition" │
│ ⚠️  No Signal: "Wait 2-3 mins or move to   │
│    open area"                               │
└─────────────────────────────────────────────┘
         │
         ▼
   [End with Success/Instruction Message]
```

#### A9. Not Near Vehicle - Callback Options
```
┌─────────────────────────────────────────────┐
│ Can you go to vehicle or should we call     │
│ back later?                                 │
│ 1️⃣ I can go to the vehicle                 │
│ 2️⃣ Call back later                         │
└─────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
   [A8: Ignition Fix]         [Schedule Callback] → [End]
```

#### A10. Send Alert to Contact Person
```
Send breakdown message to provided number:
- Supervisor: "You are the supervisor. Press 1 for assistance."  
- Driver: "You are the driver. Press 1 for assistance."
- Manager: "We are here to help you. Press 1 for assistance."

When they press 1 → [A6: GPS Repair Flow]
```

---

### 3. PATH B: USER-INITIATED CONVERSATION

#### B1. User Greeting
```
User: "Hi", "Hello", "Namaste", etc.
↓
System: Welcome message with main menu
```

#### B2. Main Menu
```
┌─────────────────────────────────────────────┐
│ What kind of help do you need?              │
│ 1️⃣ Vehicle Problem                         │
│ 2️⃣ Engineer Chahiye                        │
│ Reply with 1 or 2                          │
└─────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
   [B3: Both lead to same flow]
```

#### B3. Unified Flow (Both Options 1 & 2)
```
┌─────────────────────────────────────────────┐
│ Are we talking to the manager of [COMPANY]? │
│ 1️⃣ हाँ / Yes                               │
│ 2️⃣ नहीं / No                                │
└─────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
    [Same as A4]              [Same as A5]
```

*From here, the flow follows the same paths as the Proactive Alert flow (A4-A10)*

---

## 🔄 GPS Repair Flow (Core Technical Process)

This is the unified technical flow used by all user types:

```
┌─────────────────────────────────────────────┐
│ STATE: GPS_REPAIR_NEAR_VEHICLE              │
│ Are you near the vehicle?                   │
│ 1️⃣ Yes  2️⃣ No                             │
└─────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
┌─────────────────────┐    ┌─────────────────────┐
│ GPS_REPAIR_IGNITION │    │ GPS_REPAIR_SCHEDULE │
│ Turn on ignition    │    │ _CALLBACK           │
│ Press 1 when done   │    │ 1️⃣ Go to vehicle   │
└─────────────────────┘    │ 2️⃣ Call later      │
         │                 └─────────────────────┘
         ▼                          │
┌─────────────────────┐             ▼
│ SUCCESS MESSAGE     │    ┌─────────────────────┐
│ GPS should work now │    │ If 1: → Ignition   │
│ Wait 2-3 minutes    │    │ If 2: → Callback   │
│ [CONVERSATION END]  │    │       → End        │
└─────────────────────┘    └─────────────────────┘
```

---

## 📱 Message Templates by Contact Type

### Breakdown Alert Messages

**For Driver:**
```
🚨 वाहन सहायता अलर्ट / Vehicle Support Alert

वाहन में तकनीकी समस्या है - GPS काम नहीं कर रहा है और डेटा ट्रांसमिशन रुका हुआ है।
Vehicle has technical issues - GPS is not working and data transmission has stopped.

आप ड्राइवर हैं। कृपया सहायता के लिए 1 दबाएं।
You are the driver. Please press 1 for assistance.

1️⃣ Press 1 for AI assistance
```

**For Supervisor:**
```
[Same as driver, but "आप सुपरवाइजर हैं / You are the supervisor"]
```

**For Manager/Others:**
```
[Same technical issue description]
हम आपकी सहायता के लिए यहाँ हैं।
We are here to help you.
1️⃣ Press 1 for AI assistance
```

---

## 🎯 Conversation States

### State Definitions
- `MAIN_MENU` - Initial menu selection
- `ASK_RIGHT_PERSON` - Company manager verification
- `ASK_CAN_PROVIDE_OTHER_NUMBER` - Continue vs delegate choice
- `ASK_CONTACT_TYPE` - Supervisor vs driver selection
- `ASK_CONTACT_NUMBER` - Manual number input
- `GPS_REPAIR_NEAR_VEHICLE` - GPS repair: near vehicle check
- `GPS_REPAIR_IGNITION` - GPS repair: ignition instruction  
- `GPS_REPAIR_VERIFICATION` - GPS repair: automatic status verification (10s wait + API check)
- `GPS_REPAIR_SCHEDULE_CALLBACK` - GPS repair: callback scheduling

### Legacy States (Preserved for backward compatibility)
- `ASK_PROBLEM_DESCRIPTION` - Generic problem input
- `VEHICLE_NUMBER` - Vehicle identification
- `ASK_DRIVER_AVAILABILITY` - Driver presence check
- `ASK_LOCATION` - Vehicle location
- `ASK_IGNITION` - Ignition status
- `ASK_POWER_LED` - Power LED status
- `ASK_GSM_LED` - GSM LED status  
- `ASK_GPS_LED` - GPS LED status
- `VERIFY_RESOLUTION` - Problem resolution check
- `TICKET_CONFIRMATION` - Support ticket creation

---

## 🔧 Key Features

### 1. State Reset Logic
- State resets ONLY when breakdown alert API is called
- Ensures fresh conversations for alert recipients
- Preserves normal chat flows

### 2. Database Integration
- Automatic driver number lookup from vehicle assignments
- Company name resolution for personalized messages
- Fallback to manual input when database info unavailable

### 3. Context Management  
- Pre-creates conversation states for alert recipients
- Maintains contact type (driver/supervisor/manager) throughout flow
- Automatic routing based on user role

### 4. Bilingual Support
- All messages in Hindi and English
- Supports both script inputs and English responses
- Consistent translation across all flows

### 5. Error Handling
- Phone number validation and E.164 formatting
- Comprehensive logging for debugging
- Graceful fallbacks for missing data
- WhatsApp API error categorization

---

## 📊 Flow Summary

**Total Conversation States:** 17  
**Main Entry Points:** 2 (Proactive + User-initiated)  
**Core Flow Paths:** 3 (Manager continues, Contact delegation, Wrong person)  
**GPS Repair Sub-flows:** 3 (Near vehicle, Not near, Callback)  
**Supported Languages:** 2 (Hindi + English)  
**Contact Types:** 3 (Manager, Supervisor, Driver)

---

*This flow tree represents the current implementation as of the latest updates. All paths lead to either GPS repair completion or conversation termination with appropriate next steps.*