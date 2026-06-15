# Service Engineer Flow - Complete Implementation Plan

## Overview
This document outlines the complete implementation of the GPS Service Engineer Assignment Chatbot flow based on the provided PDF specification.

## Flow Structure

### 1. Initial Questions (Q1-Q2)
- **Q1**: Kya yeh vehicle aapki hai? (Is this your vehicle?)
  - Yes → Q2
  - No → End Case

- **Q2**: Vehicle kis wajah se inactive hai? (Why is vehicle inactive?)
  - 8 options lead to 8 different flows

### 2. Eight Main Flows

#### A. WORKSHOP FLOW (Q3-Q4)
- Q3: Workshop mein repair ke liye hai?
  - Yes → Close Case
  - No → Q4 (current location) → Manual Verification

#### B. ACCIDENT FLOW (Q5)
- Q5: GPS device accident mein damage hua?
  - Yes → Service Request
  - No → Close Case

#### C. BATTERY DISCONNECT FLOW (Q6-Q8)
- Q6: Battery maintenance ke liye disconnect?
  - Yes → Q7
  - No → Q8
- Q7: GPS device dobara install karna hai?
  - Yes → Service Request
  - No → Close Case
- Q8: GPS data receive nahi ho raha?
  - Yes → Service Request
  - No → Close Case

#### D. GPS REMOVED FLOW (Q9-Q11)
- Q9: GPS device remove ho gaya?
  - Yes → Q10
  - No → ?
- Q10: GPS kisne remove kiya? (Customer/Workshop/Unknown)
- Q11: GPS dobara install karwana hai?
  - Yes → Service Request
  - No → Close Case

#### E. GPS DAMAGED FLOW (Q12-Q13)
- Q12: GPS physically damage hua?
  - Yes → Q13
  - No → Close Case
- Q13: GPS replacement zarurat hai?
  - Yes → Service Request
  - No → Close Case

#### F. VEHICLE STANDING FLOW (Q14-Q16)
- Q14: Vehicle kitne samay se standing?
  - <24hrs → Q16
  - 24-48hrs → Q16
  - >48hrs → Q15
- Q15: GPS inspection zarurat hai?
  - Yes → Service Request
  - No → Close Case
- Q16: GPS data aa raha hai?
  - Yes → Close Case
  - No → Service Request

#### G. RUNNING VEHICLE BUT NO GPS DATA FLOW (Q17-Q22)
- Q17: Vehicle chal rahi hai?
  - No → Standing Vehicle Flow
  - Yes → Q18-Q22
- Q18: Driver ka naam?
- Q19: Driver ka mobile?
- Q20: Current location?
- Q21: Vehicle inspection ke liye available?
  - No → Q22
  - Yes → Service Request
- Q22: Vehicle kab available hogi? (Date & Time) → Service Request

#### H. OTHER ISSUE FLOW (Q23-Q24)
- Q23: Issue describe karein (Text Input)
- Q24: Issue GPS device se related hai?
  - Yes → Service Request
  - No → Close Case

### 3. Service Request Details (Q25-Q34)
When Service Request is required, collect:
- Q25: Vehicle Number
- Q26: Vehicle Owner Name
- Q27: Owner Mobile Number
- Q28: Current Vehicle Location
- Q29: Driver Name
- Q30: Driver Mobile Number
- Q31: Vehicle Available? (Yes/No)
- Q32: Preferred Visit Date
- Q33: Preferred Visit Time
- Q34: Issue Type (GPS Not Working, GPS Removed, GPS Damaged, Battery Related, GPS Reinstallation, Accident Related, Other)

### 4. Engineer Assignment (Q35)
- Q35: Nearest service engineer assign karein?
  - Yes → Create Ticket → Assign Engineer → Notify Customer
  - No → Keep Ticket On Hold

## Implementation Structure

### Files to Create/Modify

1. **app/services/flow_handlers/** (new directory)
   - `__init__.py`
   - `workshop_flow.py`
   - `accident_flow.py`
   - `battery_flow.py`
   - `gps_removed_flow.py`
   - `gps_damaged_flow.py`
   - `vehicle_standing_flow.py`
   - `vehicle_running_flow.py`
   - `other_issue_flow.py`
   - `service_request_collector.py` (handles Q25-Q34)

2. **app/services/service_engineer_flow_service.py** (modify)
   - Complete main orchestration
   - Route to flow handlers
   - Handle Q35 (engineer assignment)

3. **app/services/state_manager.py** (already has all states)
   - All ConversationStep enums already defined

4. **app/db/models/ticket.py** (already updated)
   - All fields already present

## State Flow Mapping

### ConversationStep Enum Usage

```python
# Workshop Flow States
WORKSHOP_CONFIRMATION = Q3

# Accident Flow States  
ACCIDENT_WORKSHOP_CONFIRMATION = Q5

# Battery Flow States
BATTERY_MAINTENANCE_CONFIRMATION = Q6
# (needs Q7, Q8 states)

# GPS Removed Flow States
GPS_REMOVED_REINSTALL_DATE = Q11 (date)
GPS_REMOVED_REINSTALL_TIME = Q11 (time)
GPS_REMOVED_LOCATION = (location collection)
GPS_REMOVED_CONTACT = (contact collection)
GPS_REMOVED_AVAILABILITY = (availability check)

# GPS Damaged Flow States
GPS_DAMAGED_LOCATION = Q20/Q28
GPS_DAMAGED_CONTACT = (contact collection)
GPS_DAMAGED_INSPECTION_DATE = (visit date)
GPS_DAMAGED_INSPECTION_TIME = (visit time)

# Vehicle Running Flow States
VEHICLE_RUNNING_DRIVER_NAME = Q18
VEHICLE_RUNNING_DRIVER_MOBILE = Q19
VEHICLE_RUNNING_LOCATION = Q20
VEHICLE_RUNNING_INSPECTION_DATE = Q21/Q22 (date)
VEHICLE_RUNNING_INSPECTION_TIME = Q21/Q22 (time)

# Vehicle Standing Flow States
VEHICLE_STANDING_DURATION = Q14
VEHICLE_STANDING_LOCATION = (location)
VEHICLE_STANDING_INSPECTION_DATE = (visit date)
VEHICLE_STANDING_INSPECTION_TIME = (visit time)

# Data Collection States (Q25-Q34)
DATA_COLLECTION_VEHICLE_NUMBER = Q25
DATA_COLLECTION_OWNER_NAME = Q26
DATA_COLLECTION_OWNER_MOBILE = Q27
DATA_COLLECTION_DRIVER_NAME = Q29
DATA_COLLECTION_DRIVER_MOBILE = Q30
DATA_COLLECTION_LOCATION = Q28
DATA_COLLECTION_VISIT_DATE = Q32
DATA_COLLECTION_VISIT_TIME = Q33
DATA_COLLECTION_ISSUE_TYPE = Q34

# Engineer Assignment
ENGINEER_ASSIGNMENT = Q35
```

## Additional State Mappings Needed

Need to add these to ConversationStep enum:
- `BATTERY_GPS_REINSTALL_CONFIRMATION` (Q7)
- `BATTERY_GPS_DATA_CHECK` (Q8)
- `GPS_REMOVED_WHO_REMOVED` (Q10)
- `GPS_REMOVED_REINSTALL_CONFIRMATION` (Q11 yes/no)
- `GPS_DAMAGED_PHYSICAL_DAMAGE` (Q12)
- `GPS_DAMAGED_REPLACEMENT_NEEDED` (Q13)
- `VEHICLE_STANDING_INSPECTION_NEEDED` (Q15)
- `VEHICLE_STANDING_GPS_DATA_CHECK` (Q16)
- `VEHICLE_RUNNING_CONFIRMATION` (Q17)
- `VEHICLE_RUNNING_AVAILABILITY` (Q21)
- `VEHICLE_RUNNING_AVAILABLE_DATE` (Q22)
- `OTHER_ISSUE_DESCRIPTION` (Q23)
- `OTHER_ISSUE_GPS_RELATED` (Q24)
- `DATA_COLLECTION_VEHICLE_AVAILABLE` (Q31)

## Implementation Strategy

### Phase 1: Update State Manager
Add missing ConversationStep enums

### Phase 2: Create Service Request Collector
Handles Q25-Q34 (data collection) - shared across all flows

### Phase 3: Implement Each Flow Handler
One file per flow, handling all questions in that flow

### Phase 4: Update Main Service
Wire everything together in service_engineer_flow_service.py

### Phase 5: Testing
Test each flow end-to-end

## Data Validation

### Phone Number
- Format: 10 digits or with country code
- Validation regex: `^[+]?[0-9]{10,15}$`

### Date Format
- Expected: DD/MM/YYYY
- Parse and validate

### Time Format
- Expected: HH:MM or 12-hour format
- Convert to 24-hour format

### Location
- Free text, minimum 5 characters

## Error Handling

1. **Invalid Input**: Re-ask with examples
2. **Timeout**: Send reminder after 24 hours
3. **Flow Interruption**: Allow "reset" command
4. **Data Missing**: Collect before ticket creation

## Ticket Status Flow

```
OPEN → ASSIGNED → IN_PROGRESS → RESOLVED → CLOSED
     ↓
   ON_HOLD
```

## Next Steps

1. ✅ Document complete flow
2. 🔄 Add missing ConversationStep enums
3. 🔄 Implement service_request_collector.py
4. 🔄 Implement all 8 flow handlers
5. 🔄 Update main service orchestrator
6. 🔄 Test each flow
7. 🔄 Deploy and monitor
