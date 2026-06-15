# GPS Service Engineer Assignment Flow

```text
Vehicle Offline Detected
↓
Check Inactive Duration
↓
┌─────────────────────────────┐
│ Inactive > 48 Hours ?       │
└──────────────┬──────────────┘
               │
        YES    │    NO
               │
               ↓
     Auto Close Case
   (Long Parked Vehicle)
               │
               ▼
              END

NO
↓
Send Initial Message

"Your vehicle has been inactive.
Please share:
1. Current vehicle location
2. Reason for inactivity"

↓
Customer Reply
↓
LLM Intent Classification
↓

├─────────────────────────────────────────────┐
│ Workshop                                    │
├─────────────────────────────────────────────┤
│ Ask: Is vehicle currently in workshop?      │
│                                              │
│ YES → Close Case                             │
│ NO  → Manual Review                          │
└─────────────────────────────────────────────┘

├─────────────────────────────────────────────┐
│ Accident                                    │
├─────────────────────────────────────────────┤
│ Ask: Is vehicle currently under repair?     │
│                                              │
│ YES → Close Case                             │
│ NO  → Manual Review                          │
└─────────────────────────────────────────────┘

├─────────────────────────────────────────────┐
│ Battery Disconnect                          │
├─────────────────────────────────────────────┤
│ Ask: Maintenance or battery replacement?    │
│                                              │
│ YES → Close Case                             │
│ NO  → Manual Review                          │
└─────────────────────────────────────────────┘

├─────────────────────────────────────────────┐
│ GPS Removed                                 │
├─────────────────────────────────────────────┤
│ Collect Required Details                    │
│ • Vehicle Number                            │
│ • Location                                  │
│ • Contact Person                            │
│ • GPS Removal Details                       │
│                                              │
│ Create Service Ticket                       │
│ Assign Nearest Engineer                     │
│ Notify Customer                             │
└─────────────────────────────────────────────┘

├─────────────────────────────────────────────┐
│ GPS Damaged                                 │
├─────────────────────────────────────────────┤
│ Collect Required Details                    │
│ • Vehicle Number                            │
│ • Location                                  │
│ • Contact Person                            │
│ • Damage Description                        │
│                                              │
│ Create Service Ticket                       │
│ Assign Nearest Engineer                     │
│ Notify Customer                             │
└─────────────────────────────────────────────┘

├─────────────────────────────────────────────┐
│ Vehicle Running                             │
├─────────────────────────────────────────────┤
│ Collect Driver Details                      │
│ • Driver Name                               │
│ • Driver Contact                            │
│ • Current Location                          │
│                                              │
│ Create Service Ticket                       │
│ Assign Nearest Engineer                     │
│ Notify Customer                             │
└─────────────────────────────────────────────┘

├─────────────────────────────────────────────┐
│ Vehicle Standing (<48 Hours)                │
├─────────────────────────────────────────────┤
│ Collect Required Details                    │
│ • Location                                  │
│ • Reason for Standing                       │
│                                              │
│ Create Service Ticket                       │
│ Assign Nearest Engineer                     │
│ Notify Customer                             │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Unknown                                     │
└─────────────────────────────────────────────┘
                    ↓
        Ask Additional Questions
                    ↓
             Reclassify Intent
                    ↓
      ┌──────────────────────────┐
      │ GPS Related Issue ?      │
      └───────────┬──────────────┘
                  │
          YES     │     NO
                  │
                  ↓
      Route To Correct Flow
                        │
                        ↓
                   Close Case


======================================================
FINAL SYSTEM FLOW
======================================================

Vehicle Offline Detected
↓
Check Inactive Duration
↓
Customer Contact
↓
Reason Collection
↓
LLM Intent Classification
↓
Required Detail Collection
↓
Service Ticket Creation
↓
Nearest Engineer Assignment
↓
Customer Notification
↓
Engineer Visit
↓
Issue Resolution
↓
Ticket Closure
```
