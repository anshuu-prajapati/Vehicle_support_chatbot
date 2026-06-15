# REVISED IMPLEMENTATION PLAN
## Service Engineer Assignment System - Surgical Approach

**Based on**: Comprehensive codebase analysis  
**Strategy**: Maximum reuse, minimal duplication, surgical modifications  
**Timeline**: 10 days  

---

## ARCHITECTURAL DECISIONS

### ✅ **REUSE - Ticket Model (Extended)**
**Decision**: Extend existing Ticket model instead of creating ServiceRequest  
**Rationale**:
- Ticket model already has: ticket_number, customer_phone, problem, status
- Avoids duplication of ticket management logic
- Maintains consistency with existing system
- Simple migration to add new fields

### ✅ **REUSE - State Manager**
**Decision**: Use existing StateManager, just add new conversation steps  
**Rationale**:
- Already handles: state persistence, context storage, transactions
- Proven, tested, reliable
- No need for new state management system

### ✅ **REUSE - Service Layer**
**Decision**: Extend ticket_service.py instead of creating service_request_service.py  
**Rationale**:
- Existing pattern for ticket creation
- Just needs additional functions: update, close, assign_engineer
- Maintains single responsibility

### ✅ **REFACTOR - Flow Handler**
**Decision**: Create modular flow handlers, keep old flow for backward compat  
**Rationale**:
- support_flow_service.py is 2888 lines - needs modularization
- Separate concerns: old GPS repair vs new service engineer assignment
- Easier testing and maintenance

---

## IMPLEMENTATION SEQUENCE

### **SPRINT 1: Foundation (Days 1-2)**

#### Task 1.1: Extend Ticket Model
**File**: `alembic/versions/0005_extend_tickets_for_service_engineer.py`

```python
"""Extend tickets table for service engineer assignment

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-13

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('tickets', sa.Column('issue_type', sa.String(50), nullable=True))
    op.add_column('tickets', sa.Column('vehicle_number', sa.String(100), nullable=True))
    op.add_column('tickets', sa.Column('owner_name', sa.String(100), nullable=True))
    op.add_column('tickets', sa.Column('owner_mobile', sa.String(20), nullable=True))
    op.add_column('tickets', sa.Column('driver_name', sa.String(100), nullable=True))
    op.add_column('tickets', sa.Column('driver_mobile', sa.String(20), nullable=True))
    op.add_column('tickets', sa.Column('location', sa.String(255), nullable=True))
    op.add_column('tickets', sa.Column('visit_date', sa.Date(), nullable=True))
    op.add_column('tickets', sa.Column('visit_time', sa.Time(), nullable=True))
    op.add_column('tickets', sa.Column('reinstallation_date', sa.Date(), nullable=True))
    op.add_column('tickets', sa.Column('reinstallation_time', sa.Time(), nullable=True))
    op.add_column('tickets', sa.Column('vehicle_available', sa.Boolean(), nullable=True))
    op.add_column('tickets', sa.Column('vehicle_available_date', sa.Date(), nullable=True))
    op.add_column('tickets', sa.Column('vehicle_available_time', sa.Time(), nullable=True))
    op.add_column('tickets', sa.Column('inspection_date', sa.Date(), nullable=True))
    op.add_column('tickets', sa.Column('inspection_time', sa.Time(), nullable=True))
    op.add_column('tickets', sa.Column('standing_duration', sa.String(50), nullable=True))
    op.add_column('tickets', sa.Column('closure_reason', sa.String(100), nullable=True))
    op.add_column('tickets', sa.Column('assigned_engineer_id', sa.Integer(), nullable=True))
    
    # Add foreign key for assigned_engineer_id
    op.create_foreign_key(
        'fk_tickets_assigned_engineer_id',
        'tickets', 'users',
        ['assigned_engineer_id'], ['id']
    )
    
    # Add index for vehicle_number for faster lookups
    op.create_index('ix_tickets_vehicle_number', 'tickets', ['vehicle_number'])
    op.create_index('ix_tickets_issue_type', 'tickets', ['issue_type'])

def downgrade():
    op.drop_index('ix_tickets_issue_type', 'tickets')
    op.drop_index('ix_tickets_vehicle_number', 'tickets')
    op.drop_constraint('fk_tickets_assigned_engineer_id', 'tickets', type_='foreignkey')
    
    op.drop_column('tickets', 'assigned_engineer_id')
    op.drop_column('tickets', 'closure_reason')
    op.drop_column('tickets', 'standing_duration')
    op.drop_column('tickets', 'inspection_time')
    op.drop_column('tickets', 'inspection_date')
    op.drop_column('tickets', 'vehicle_available_time')
    op.drop_column('tickets', 'vehicle_available_date')
    op.drop_column('tickets', 'vehicle_available')
    op.drop_column('tickets', 'reinstallation_time')
    op.drop_column('tickets', 'reinstallation_date')
    op.drop_column('tickets', 'visit_time')
    op.drop_column('tickets', 'visit_date')
    op.drop_column('tickets', 'location')
    op.drop_column('tickets', 'driver_mobile')
    op.drop_column('tickets', 'driver_name')
    op.drop_column('tickets', 'owner_mobile')
    op.drop_column('tickets', 'owner_name')
    op.drop_column('tickets', 'vehicle_number')
    op.drop_column('tickets', 'issue_type')
```

#### Task 1.2: Update Ticket Model
**File**: `app/db/models/ticket.py` (MODIFY)

```python
# Add new columns to model
class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(50), unique=True, nullable=False)
    customer_phone = Column(String(20), nullable=False)
    driver_phone = Column(String(20), nullable=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    problem = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, server_default="OPEN")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # NEW COLUMNS
    issue_type = Column(String(50), nullable=True)
    vehicle_number = Column(String(100), nullable=True)
    owner_name = Column(String(100), nullable=True)
    owner_mobile = Column(String(20), nullable=True)
    driver_name = Column(String(100), nullable=True)
    driver_mobile = Column(String(20), nullable=True)
    location = Column(String(255), nullable=True)
    visit_date = Column(Date, nullable=True)
    visit_time = Column(Time, nullable=True)
    reinstallation_date = Column(Date, nullable=True)
    reinstallation_time = Column(Time, nullable=True)
    vehicle_available = Column(Boolean, nullable=True)
    vehicle_available_date = Column(Date, nullable=True)
    vehicle_available_time = Column(Time, nullable=True)
    inspection_date = Column(Date, nullable=True)
    inspection_time = Column(Time, nullable=True)
    standing_duration = Column(String(50), nullable=True)
    closure_reason = Column(String(100), nullable=True)
    assigned_engineer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    assigned_engineer = relationship("User", foreign_keys=[assigned_engineer_id])
```

#### Task 1.3: Update Ticket Schema
**File**: `app/schemas/ticket_schema.py` (MODIFY)

```python
from datetime import date, time
from enum import Enum

class IssueType(str, Enum):
    WORKSHOP = "WORKSHOP"
    ACCIDENT = "ACCIDENT"
    BATTERY_DISCONNECT = "BATTERY_DISCONNECT"
    GPS_REMOVED = "GPS_REMOVED"
    GPS_DAMAGED = "GPS_DAMAGED"
    VEHICLE_RUNNING = "VEHICLE_RUNNING"
    VEHICLE_STANDING = "VEHICLE_STANDING"
    UNKNOWN = "UNKNOWN"

class TicketCreate(BaseModel):
    customer_phone: str
    problem: str
    driver_phone: Optional[str] = None
    customer_id: Optional[int] = None
    driver_id: Optional[int] = None
    # NEW FIELDS
    issue_type: Optional[IssueType] = None
    vehicle_number: Optional[str] = None
    owner_name: Optional[str] = None
    owner_mobile: Optional[str] = None
    driver_name: Optional[str] = None
    driver_mobile: Optional[str] = None
    location: Optional[str] = None
    visit_date: Optional[date] = None
    visit_time: Optional[time] = None
    # ... other fields

class TicketUpdate(BaseModel):
    status: Optional[str] = None
    closure_reason: Optional[str] = None
    assigned_engineer_id: Optional[int] = None
    # ... other updatable fields

class TicketOut(BaseModel):
    ticket_number: str
    customer_phone: str
    driver_phone: Optional[str] = None
    problem: str
    status: str
    issue_type: Optional[str] = None
    vehicle_number: Optional[str] = None
    # ... all fields

    class Config:
        orm_mode = True
```

#### Task 1.4: Update State Manager
**File**: `app/services/state_manager.py` (MODIFY)

```python
class ConversationStep(str, Enum):
    MAIN_MENU = "MAIN_MENU"
    # ... existing steps ...
    
    # NEW: Service Engineer Assignment Flow States
    INITIAL_CUSTOMER_MESSAGE = "INITIAL_CUSTOMER_MESSAGE"
    INTENT_CLASSIFICATION = "INTENT_CLASSIFICATION"
    
    # Workshop Flow
    WORKSHOP_CONFIRMATION = "WORKSHOP_CONFIRMATION"
    
    # Accident Flow
    ACCIDENT_WORKSHOP_CONFIRMATION = "ACCIDENT_WORKSHOP_CONFIRMATION"
    
    # Battery Disconnect Flow
    BATTERY_MAINTENANCE_CONFIRMATION = "BATTERY_MAINTENANCE_CONFIRMATION"
    
    # GPS Removed Flow
    GPS_REMOVED_REINSTALL_DATE = "GPS_REMOVED_REINSTALL_DATE"
    GPS_REMOVED_REINSTALL_TIME = "GPS_REMOVED_REINSTALL_TIME"
    GPS_REMOVED_LOCATION = "GPS_REMOVED_LOCATION"
    GPS_REMOVED_CONTACT = "GPS_REMOVED_CONTACT"
    GPS_REMOVED_AVAILABILITY = "GPS_REMOVED_AVAILABILITY"
    GPS_REMOVED_AVAILABLE_DATE = "GPS_REMOVED_AVAILABLE_DATE"
    GPS_REMOVED_AVAILABLE_TIME = "GPS_REMOVED_AVAILABLE_TIME"
    
    # GPS Damaged Flow
    GPS_DAMAGED_LOCATION = "GPS_DAMAGED_LOCATION"
    GPS_DAMAGED_CONTACT = "GPS_DAMAGED_CONTACT"
    GPS_DAMAGED_INSPECTION_DATE = "GPS_DAMAGED_INSPECTION_DATE"
    GPS_DAMAGED_INSPECTION_TIME = "GPS_DAMAGED_INSPECTION_TIME"
    
    # Vehicle Running Flow
    VEHICLE_RUNNING_DRIVER_NAME = "VEHICLE_RUNNING_DRIVER_NAME"
    VEHICLE_RUNNING_DRIVER_MOBILE = "VEHICLE_RUNNING_DRIVER_MOBILE"
    VEHICLE_RUNNING_LOCATION = "VEHICLE_RUNNING_LOCATION"
    VEHICLE_RUNNING_INSPECTION_DATE = "VEHICLE_RUNNING_INSPECTION_DATE"
    VEHICLE_RUNNING_INSPECTION_TIME = "VEHICLE_RUNNING_INSPECTION_TIME"
    
    # Vehicle Standing Flow
    VEHICLE_STANDING_DURATION = "VEHICLE_STANDING_DURATION"
    VEHICLE_STANDING_LOCATION = "VEHICLE_STANDING_LOCATION"
    VEHICLE_STANDING_INSPECTION_DATE = "VEHICLE_STANDING_INSPECTION_DATE"
    VEHICLE_STANDING_INSPECTION_TIME = "VEHICLE_STANDING_INSPECTION_TIME"
    
    # Unknown Flow
    UNKNOWN_DETAIL_REQUEST = "UNKNOWN_DETAIL_REQUEST"
    UNKNOWN_RECLASSIFICATION = "UNKNOWN_RECLASSIFICATION"
    
    # Smart Data Collection
    DATA_COLLECTION_VEHICLE_NUMBER = "DATA_COLLECTION_VEHICLE_NUMBER"
    DATA_COLLECTION_OWNER_NAME = "DATA_COLLECTION_OWNER_NAME"
    DATA_COLLECTION_OWNER_MOBILE = "DATA_COLLECTION_OWNER_MOBILE"
    DATA_COLLECTION_LOCATION = "DATA_COLLECTION_LOCATION"
    DATA_COLLECTION_VISIT_DATE = "DATA_COLLECTION_VISIT_DATE"
    DATA_COLLECTION_VISIT_TIME = "DATA_COLLECTION_VISIT_TIME"
    
    # Engineer Assignment
    ENGINEER_ASSIGNMENT = "ENGINEER_ASSIGNMENT"

# Update DEFAULT_STATE_CONTEXT
DEFAULT_STATE_CONTEXT = {
    "vehicle_number": "",
    "owner_name": "",
    "owner_phone": "",
    "driver_name": "",
    "driver_phone": "",
    "issue_type": "",
    "location": "",
    "ticket_id": "",
    "contact_type": "",
    # NEW FIELDS
    "last_location": "",
    "last_activity_time": "",
    "inactive_duration_hours": 0,
    "issue_classification": "",
    "customer_response": "",
    "owner_mobile": "",
    "driver_mobile": "",
    "visit_date": "",
    "visit_time": "",
    "reinstallation_date": "",
    "reinstallation_time": "",
    "vehicle_available": None,
    "vehicle_available_date": "",
    "vehicle_available_time": "",
    "inspection_date": "",
    "inspection_time": "",
    "standing_duration": "",
    "service_request_id": "",
}
```

---

### **SPRINT 2: Core Services (Days 3-4)**

#### Task 2.1: Create Ticket Repository
**File**: `app/repositories/ticket_repository.py` (NEW)

```python
from typing import Optional, List
from sqlalchemy.orm import Session
from app.db.models.ticket import Ticket

class TicketRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, ticket_id: int) -> Optional[Ticket]:
        return self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
    
    def get_by_ticket_number(self, ticket_number: str) -> Optional[Ticket]:
        return self.db.query(Ticket).filter(Ticket.ticket_number == ticket_number).first()
    
    def get_by_vehicle_number(self, vehicle_number: str) -> List[Ticket]:
        return self.db.query(Ticket).filter(Ticket.vehicle_number == vehicle_number).all()
    
    def list_open(self, skip: int = 0, limit: int = 100) -> List[Ticket]:
        return self.db.query(Ticket).filter(Ticket.status == "OPEN").offset(skip).limit(limit).all()
    
    def create(self, **kwargs) -> Ticket:
        ticket = Ticket(**kwargs)
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket
    
    def update(self, ticket: Ticket, **kwargs) -> Ticket:
        for key, value in kwargs.items():
            if hasattr(ticket, key) and value is not None:
                setattr(ticket, key, value)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket
```

#### Task 2.2: Extend Ticket Service
**File**: `app/services/ticket_service.py` (MODIFY)

```python
# Keep existing functions, add new ones:

def update_ticket(ticket_number: str, **kwargs):
    """Update ticket fields"""
    db = SessionLocal()
    try:
        from app.repositories.ticket_repository import TicketRepository
        repo = TicketRepository(db)
        ticket = repo.get_by_ticket_number(ticket_number)
        if not ticket:
            return None
        return repo.update(ticket, **kwargs)
    finally:
        db.close()

def close_ticket(ticket_number: str, closure_reason: str):
    """Close ticket with reason"""
    return update_ticket(
        ticket_number,
        status="CLOSED",
        closure_reason=closure_reason
    )

def assign_engineer(ticket_number: str, engineer_id: int):
    """Assign engineer to ticket"""
    return update_ticket(
        ticket_number,
        assigned_engineer_id=engineer_id,
        status="ASSIGNED"
    )

def create_service_request_ticket(
    vehicle_number: str,
    issue_type: str,
    customer_phone: str,
    **kwargs
) -> Ticket:
    """Create ticket for service engineer assignment"""
    ticket_number = generate_ticket_number()
    db = SessionLocal()
    try:
        from app.repositories.ticket_repository import TicketRepository
        repo = TicketRepository(db)
        return repo.create(
            ticket_number=ticket_number,
            vehicle_number=vehicle_number,
            issue_type=issue_type,
            customer_phone=customer_phone,
            problem=f"{issue_type} - Service Request",
            status="OPEN",
            **kwargs
        )
    finally:
        db.close()
```

#### Task 2.3: Create Intent Classification Service
**File**: `app/services/intent_classification_service.py` (NEW)

```python
import logging
import re
from typing import Tuple
from app.ai.groq_llm import generate_response

logger = logging.getLogger("app.intent_classification")

CLASSIFICATION_PROMPT = """You are classifying customer messages about GPS/vehicle issues.

Categories (respond with ONLY the category name):
- WORKSHOP: Vehicle in workshop, repair center, service center
- ACCIDENT: Vehicle accident, collision, damage
- BATTERY_DISCONNECT: Battery removed, battery maintenance, battery replacement
- GPS_REMOVED: GPS removed, GPS detached, GPS निकला गया
- GPS_DAMAGED: GPS broken, GPS damaged, device damaged, GPS टूट गया
- VEHICLE_RUNNING: Vehicle running, driver driving, गाड़ी चल रही है
- VEHICLE_STANDING: Vehicle parked, driver on leave, vehicle not in use, खड़ी है
- UNKNOWN: Cannot determine from message

Customer message: "{message}"

Category:"""

INTENT_PATTERNS = {
    "WORKSHOP": [
        r"workshop", r"repair\s*center", r"service\s*center",
        r"मरम्मत", r"वर्कशॉप", r"सर्विस\s*सेंटर"
    ],
    "ACCIDENT": [
        r"accident", r"collision", r"damage", r"crash",
        r"टक्कर", r"दुर्घटना", r"एक्सीडेंट"
    ],
    "BATTERY_DISCONNECT": [
        r"battery.*remove", r"battery.*disconnect", r"battery.*maintenance",
        r"बैटरी\s*निकाल", r"बैटरी\s*हटा"
    ],
    "GPS_REMOVED": [
        r"gps.*nikal", r"gps.*remove", r"gps.*detach",
        r"gps\s*निकल", r"gps\s*हटा"
    ],
    "GPS_DAMAGED": [
        r"gps.*toot", r"gps.*damage", r"gps.*broke", r"device.*damage",
        r"gps\s*टूट", r"gps\s*खराब", r"डिवाइस\s*खराब"
    ],
    "VEHICLE_RUNNING": [
        r"vehicle.*running", r"driver.*chala", r"gaadi.*chal",
        r"गाड़ी\s*चल\s*रही", r"ड्राइवर.*चला\s*रहा"
    ],
    "VEHICLE_STANDING": [
        r"vehicle.*khadi", r"driver.*leave", r"parked",
        r"खड़ी\s*है", r"पार्क\s*है", r"छुट्टी"
    ],
}

def _regex_classify(message: str) -> str:
    """Fallback regex-based classification"""
    message_lower = message.lower()
    
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, message_lower):
                logger.info(f"Regex matched: {intent} (pattern: {pattern})")
                return intent
    
    return "UNKNOWN"

def classify_customer_intent(customer_message: str) -> Tuple[str, str]:
    """
    Classify customer message into issue type.
    
    Returns:
        Tuple of (classification, method) where method is "LLM" or "REGEX"
    """
    try:
        # Try LLM classification first
        prompt = CLASSIFICATION_PROMPT.format(message=customer_message)
        llm_response = generate_response(prompt).strip().upper()
        
        # Validate LLM response
        valid_categories = [
            "WORKSHOP", "ACCIDENT", "BATTERY_DISCONNECT",
            "GPS_REMOVED", "GPS_DAMAGED", "VEHICLE_RUNNING",
            "VEHICLE_STANDING", "UNKNOWN"
        ]
        
        if llm_response in valid_categories:
            logger.info(
                f"LLM classified message as: {llm_response}",
                extra={"message": customer_message, "classification": llm_response}
            )
            return llm_response, "LLM"
        else:
            logger.warning(
                f"LLM returned invalid category: {llm_response}, falling back to regex",
                extra={"llm_response": llm_response}
            )
            
    except Exception as e:
        logger.error(f"LLM classification failed: {str(e)}, falling back to regex")
    
    # Fallback to regex classification
    regex_result = _regex_classify(customer_message)
    logger.info(
        f"Regex classified message as: {regex_result}",
        extra={"message": customer_message, "classification": regex_result}
    )
    return regex_result, "REGEX"
```

---

### **SPRINT 3: Flow Handlers (Days 5-7)**

#### Task 3.1: Create Main Flow Service
**File**: `app/services/service_engineer_flow_service.py` (NEW)

This will be the main handler for the new workflow. Due to length, I'll show the structure:

```python
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.services.state_manager import StateManager, ConversationStep
from app.services.intent_classification_service import classify_customer_intent
from app.services.ticket_service import create_service_request_ticket, close_ticket
from app.services.vehicle_status_service import VehicleStatusService
from app.services.user_service import normalize_phone_number
from app.db.models.vehicle import Vehicle
from app.db.models.user import User

logger = logging.getLogger("app.service_engineer_flow")

def check_vehicle_inactive_duration(
    vehicle_number: str,
    db: Session
) -> tuple[bool, float, str, str]:
    """
    Check if vehicle has been inactive for more than 48 hours.
    
    Returns:
        (should_auto_close, hours_inactive, last_location, last_time)
    """
    # Implementation
    pass

def send_initial_customer_message(
    user_phone: str,
    vehicle_number: str,
    location: str,
    last_time: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """Send Q1 initial message to customer"""
    # Implementation
    pass

def handle_workshop_flow(
    user_phone: str,
    text_body: str,
    current_step: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """Handle WORKSHOP issue type flow"""
    # Implementation
    pass

def handle_accident_flow(...) -> str:
    """Handle ACCIDENT issue type flow"""
    pass

# ... 6 more flow handlers (one per issue type)

def handle_service_engineer_message(
    user,
    text_body: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """Main entry point for service engineer flow"""
    # Route to appropriate handler based on state
    pass
```

I'll provide detailed implementations in separate files for each flow handler.

---

### **SPRINT 4: Integration (Days 8-9)**

#### Task 4.1: Create Flow Router
**File**: `app/services/flow_router.py` (NEW)

```python
from sqlalchemy.orm import Session
from app.services.state_manager import StateManager, ConversationStep
from app.services.support_flow_service import handle_support_message as handle_gps_repair_flow
from app.services.service_engineer_flow_service import handle_service_engineer_message

# Old GPS repair flow states
OLD_GPS_REPAIR_STATES = [
    ConversationStep.GPS_REPAIR_NEAR_VEHICLE.value,
    ConversationStep.GPS_REPAIR_TIME_ESTIMATE.value,
    ConversationStep.GPS_REPAIR_WAITING_FOR_DRIVER.value,
    ConversationStep.GPS_REPAIR_CHECK_IGNITION.value,
    ConversationStep.GPS_REPAIR_CUT_OUT.value,
    ConversationStep.GPS_REPAIR_IGNITION.value,
    ConversationStep.GPS_REPAIR_VERIFICATION.value,
    ConversationStep.GPS_REPAIR_RECHECK.value,
    ConversationStep.GPS_REPAIR_GROUND_WIRE_FIND.value,
    ConversationStep.GPS_REPAIR_GROUND_WIRE_TOUCH.value,
    ConversationStep.GPS_REPAIR_GROUND_WIRE_VERIFY.value,
    ConversationStep.GPS_REPAIR_FINAL_CHECK.value,
    ConversationStep.GPS_REPAIR_ENGINEER_DISPATCH.value,
]

def route_message(user, text_body: str, state_manager: StateManager, db: Session) -> str:
    """
    Route message to appropriate flow handler.
    
    - Old GPS repair states → Old flow (backward compatibility)
    - New service engineer states → New flow
    - Greetings/Menu → New flow
    """
    state = state_manager.get_state(user.phone_number)
    
    # Route to old GPS repair flow if in old states
    if state and state.current_step in OLD_GPS_REPAIR_STATES:
        return handle_gps_repair_flow(user, text_body, state_manager, db)
    
    # Route to new service engineer flow
    return handle_service_engineer_message(user, text_body, state_manager, db)
```

#### Task 4.2: Update Webhook
**File**: `app/api/webhook.py` (MODIFY)

```python
# Change this line:
# answer = handle_support_message(user, text_body, state_manager, db)

# To:
from app.services.flow_router import route_message
answer = route_message(user, text_body, state_manager, db)
```

#### Task 4.3: Extend Tickets API
**File**: `app/api/tickets.py` (MODIFY)

```python
# Add new endpoints:

@router.patch("/{ticket_number}/assign")
def assign_engineer_to_ticket(ticket_number: str, engineer_id: int):
    from app.services.ticket_service import assign_engineer
    ticket = assign_engineer(ticket_number, engineer_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@router.patch("/{ticket_number}/close")
def close_ticket_endpoint(ticket_number: str, closure_reason: str):
    from app.services.ticket_service import close_ticket
    ticket = close_ticket(ticket_number, closure_reason)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket
```

---

## TESTING STRATEGY

### Unit Tests
- ✅ Intent classification (all 8 categories)
- ✅ Each flow handler (workshop, accident, etc.)
- ✅ Ticket service functions (update, close, assign)
- ✅ State transitions

### Integration Tests
- ✅ End-to-end workshop flow (auto-close)
- ✅ End-to-end GPS removed flow (service request created)
- ✅ End-to-end vehicle standing flow (<48hrs and >48hrs)
- ✅ Flow routing (old vs new)

### Manual Tests
- ✅ WhatsApp conversation testing
- ✅ Hindi/English bilingual responses
- ✅ State persistence across messages

---

## DEPLOYMENT CHECKLIST

### Pre-Deployment
- [ ] Run migration in staging
- [ ] Test rollback
- [ ] Verify old conversations still work
- [ ] Test new flows end-to-end

### Deployment
- [ ] Backup database
- [ ] Run migration
- [ ] Deploy code
- [ ] Monitor logs for errors
- [ ] Test with real WhatsApp account

### Post-Deployment
- [ ] Monitor classification accuracy
- [ ] Track ticket creation rate
- [ ] Verify no breaking changes
- [ ] Collect user feedback

---

## SUMMARY

**Files to CREATE**: 15  
**Files to MODIFY**: 7  
**Files UNCHANGED**: 20+  

**Code Reuse**: ~85%  
**Timeline**: 10 days  
**Risk Level**: Low (surgical approach with backward compatibility)  

**Key Success Factors**:
1. ✅ Extend Ticket model instead of creating ServiceRequest
2. ✅ Reuse StateManager without changes
3. ✅ Extend ticket_service instead of creating duplicate
4. ✅ Modular flow handlers for maintainability
5. ✅ Flow router for backward compatibility
6. ✅ Comprehensive testing before deployment
