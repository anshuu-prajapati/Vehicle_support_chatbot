# Vehicle Support Chatbot - Complete Flow Chart (Single Page Print)

```
                    VEHICLE SUPPORT CHATBOT - COMPLETE CONVERSATION FLOW
                                        
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         ENTRY POINTS                                                   │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  A) PROACTIVE ALERT                           │  B) USER GREETING                                     │
│     API: /send-breakdown-alerts               │     User: "Hi", "Hello", "Namaste"                   │
│     🚨 Vehicle Alert: GPS not working         │     System: Welcome + Main Menu                       │
│     1️⃣ Press 1 for AI assistance            │     1️⃣ Vehicle Problem  2️⃣ Engineer Chahiye        │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
                              │                                           │
                              ▼                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                           COMPANY MANAGER VERIFICATION                                                  │
│                     Are we talking to manager of [COMPANY]?                                           │
│                           1️⃣ हाँ/Yes    2️⃣ नहीं/No                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
                              │                                           │
                        ┌─────▼─────┐                               ┌─────▼─────┐
                        │  MANAGER  │                               │   WRONG   │
                        │  SAYS YES │                               │  PERSON   │
                        └─────┬─────┘                               └─────┬─────┘
                              │                                           │
                              ▼                                           ▼
┌─────────────────────────────────────────────────────────────────┐ ┌─────────────────────┐
│              CONTINUE OR DELEGATE                               │ │  PROVIDE CORRECT    │
│    Should we continue with you or talk with somebody else?     │ │  MANAGER NUMBER     │
│         1️⃣ Continue with me    2️⃣ Talk with someone else      │ │                     │
└─────────────────────────────────────────────────────────────────┘ │  Send alert to      │
                              │                         │           │  correct person     │
                    ┌─────────▼─────────┐     ┌─────────▼─────────┐ │  [END]              │
                    │   CONTINUE WITH   │     │   TALK WITH       │ └─────────────────────┘
                    │     MANAGER       │     │ SOMEONE ELSE      │
                    │ [GPS REPAIR FLOW] │     └─────────┬─────────┘
                    └───────────────────┘               │
                                                        ▼
                                        ┌─────────────────────────────────────┐
                                        │         CONTACT SELECTION           │
                                        │  Should we contact supervisor       │
                                        │         or driver?                  │
                                        │  1️⃣ Supervisor                     │
                                        │  2️⃣ Driver (number: [FROM DB])     │
                                        └─────────────────────────────────────┘
                                                        │
                                        ┌───────────────┼───────────────┐
                                        │               │               │
                                        ▼               ▼               ▼
                                ┌───────────────┐ ┌─────────────┐ ┌─────────────┐
                                │  SUPERVISOR   │ │   DRIVER    │ │ NO DB INFO  │
                                │ Ask for phone │ │ Use DB num  │ │ Ask manual  │
                                │    number     │ │ Auto send   │ │   number    │
                                └───────────────┘ └─────────────┘ └─────────────┘
                                        │               │               │
                                        └───────────────┼───────────────┘
                                                        │
                                                        ▼
                                        ┌─────────────────────────────────────┐
                                        │      SEND BREAKDOWN ALERT           │
                                        │                                     │
                                        │ Supervisor: "You are supervisor"    │
                                        │ Driver: "You are driver"            │
                                        │ Manager: "We are here to help"      │
                                        │                                     │
                                        │ All: "1️⃣ Press 1 for AI assistance"│
                                        └─────────────────────────────────────┘
                                                        │
                                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   ENHANCED GPS REPAIR FLOW                                            │
│                            (UNIFIED FOR ALL USER TYPES + AUTO VERIFICATION)                         │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                              Are you near the vehicle?                                              │
│                                1️⃣ हाँ/Yes   2️⃣ नहीं/No                                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
                              │                                           │
                    ┌─────────▼─────────┐                       ┌─────────▼─────────┐
                    │     NEAR VEHICLE  │                       │   NOT NEAR        │
                    │                   │                       │   VEHICLE         │
                    │ Turn on ignition  │                       │                   │
                    │ Press 1 when done │                       │ Can you go to     │
                    └─────────┬─────────┘                       │ vehicle or call   │
                              │                                 │ back later?       │
                              ▼                                 │ 1️⃣ Go  2️⃣ Later   │
                    ┌─────────────────────┐                     └─────────┬─────────┘
                    │  🔍 AUTO GPS        │                               │
                    │   VERIFICATION      │                     ┌─────────┼─────────┐
                    │                     │                     │         │         │
                    │ • Wait 10 seconds   │                     ▼         ▼         ▼
                    │ • Check via API     │            ┌────────────┐ ┌─────────────┐
                    │ • Smart feedback    │            │ GO TO      │ │  SCHEDULE   │
                    └─────────┬─────────┘              │ IGNITION   │ │  CALLBACK   │
                              │                        │   STEP     │ │    [END]    │
                              ▼                        └────────────┘ └─────────────┘
                    ┌─────────────────────┐
                    │  INTELLIGENT        │
                    │  RESPONSE:          │
                    │                     │
                    │ ✅ GPS Working      │
                    │ ⚠️ Ignition Off     │
                    │ ⚠️ No GPS Signal    │
                    │                     │
                    │   [CONVERSATION     │
                    │        END]         │
                    └─────────────────────┘

═══════════════════════════════════════════════════════════════════════════════════════════════════════

                                        CONVERSATION STATES
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ MAIN_MENU → ASK_RIGHT_PERSON → ASK_CAN_PROVIDE_OTHER_NUMBER → ASK_CONTACT_TYPE → ASK_CONTACT_NUMBER  │
│                                         ↓                                                             │
│                              GPS_REPAIR_NEAR_VEHICLE                                                 │
│                                    ↓        ↓                                                        │
│                         GPS_REPAIR_IGNITION → GPS_REPAIR_VERIFICATION                               │
│                                    ↓              ↓                                                  │
│                              [Auto Verification]  GPS_REPAIR_SCHEDULE_CALLBACK                      │
│                                    ↓                                                                 │
│                               [Smart Response & End]                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                         KEY FEATURES
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ • Bilingual Support (Hindi/English) • Database Driver Lookup • Phone Validation (E.164)            │
│ • State Reset on API Call • Pre-created Contact States • WhatsApp Integration                       │
│ • Company Name Resolution • Comprehensive Error Handling • Unified GPS Repair Process               │
│ • 🆕 AUTOMATIC GPS VERIFICATION • 10-Second Wait with Logging • Real-time Status Checking           │
│ • 🆕 INTELLIGENT FEEDBACK • Dynamic Responses Based on Actual Vehicle Data                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                     SAMPLE MESSAGES
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ BREAKDOWN ALERT: "🚨 Vehicle Alert - GPS not working, data transmission stopped"                     │
│ GPS REPAIR: "We need your help to fix GPS system. Are you near vehicle?"                          │
│ 🆕 AUTO VERIFICATION: "🔍 Checking GPS status... Please wait." [10s wait + API check]              │
│ 🆕 SUCCESS: "✅ GPS is updating! Location: 28.613900, 77.209000 🎉"                               │
│ 🆕 IGNITION OFF: "⚠️ Vehicle ignition is still off. Please turn on ignition."                     │
│ 🆕 NO SIGNAL: "⚠️ Ignition on but no GPS signal. Wait 2-3 minutes or move to open area."          │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```