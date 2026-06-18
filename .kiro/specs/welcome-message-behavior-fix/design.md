# Welcome Message Behavior Fix - Design Document

## Overview

This design implements intelligent welcome message control to ensure the greeting is only shown to new users, not during active conversations. The solution adds multiple layers of checks before triggering the welcome message.

## Architecture Approach

### Design Philosophy
**Guard-First Pattern**: Add protective checks at the earliest possible point in the message handling flow to prevent inappropriate welcome messages before they happen.

### Key Principles
1. **Fail-Safe**: Default to NOT showing welcome unless explicitly appropriate
2. **Context-Aware**: Always check conversation state before any action
3. **Layer Defense**: Multiple checks at different stages
4. **Non-Invasive**: Minimal changes to existing flow handlers

## Component Design

### 1. State Classification Helper

**File**: `app/services/state_classifier.py` (NEW)

**Purpose**: Centralized logic to classify conversation states and determine welcome eligibility

**Functions**:

```python
def is_active_flow(current_step: Optional[str]) -> bool:
    """
    Determine if conversation is in an active flow.
    
    Active = user is mid-conversation, waiting for response or collecting data
    Not Active = MAIN_MENU, None, or recently completed
    
    Args:
        current_step: Current ConversationStep value
        
    Returns:
        True if in active flow, False otherwise
    """

def is_completion_state(current_step: Optional[str]) -> bool:
    """
    Check if current step indicates flow completion.
    
    Completion states:
    - States that mark end of flow (before MAIN_MENU reset)
    - May have completion marker in context
    
    Args:
        current_step: Current ConversationStep value
        
    Returns:
        True if flow just completed, False otherwise
    """

def should_show_welcome(
    current_step: Optional[str],
    context: Dict[str, Any],
    is_greeting: bool
) -> bool:
    """
    Master decision function for welcome message display.
    
    Logic:
    1. If no state and is greeting → YES
    2. If active flow → NO
    3. If completed flow → NO (even if greeting)
    4. If MAIN_MENU but recent activity → NO
    5. Default → NO (fail-safe)
    
    Args:
        current_step: Current conversation step
        context: Conversation context dict
        is_greeting: Whether message is a greeting
        
    Returns:
        True only if welcome should be shown
    """

def get_active_flow_steps() -> Set[str]:
    """
    Return set of all steps that represent active flows.
    
    Returns:
        Set of ConversationStep values that are "active"
    """

def get_completion_markers() -> Set[str]:
    """
    Return set of context keys that indicate completion.
    
    Returns:
        Set of context keys like "flow_completed", "case_closed", etc.
    """
```

**Data Structures**:

```python
# Active flow steps (exclude these from welcome)
ACTIVE_FLOW_STEPS = {
    # Workshop Flow
    ConversationStep.WORKSHOP_CONFIRMATION,
    
    # Accident Flow  
    ConversationStep.ACCIDENT_WORKSHOP_CONFIRMATION,
    
    # Battery Flow
    ConversationStep.BATTERY_MAINTENANCE_CONFIRMATION,
    ConversationStep.BATTERY_GPS_REINSTALL_CONFIRMATION,
    ConversationStep.BATTERY_GPS_DATA_CHECK,
    
    # GPS Removed Flow
    ConversationStep.GPS_REMOVED_REINSTALL_DATE,
    ConversationStep.GPS_REMOVED_LOCATION,
    ConversationStep.GPS_REMOVED_CONTACT,
    ConversationStep.GPS_REMOVED_AVAILABILITY,
    ConversationStep.GPS_REMOVED_AVAILABLE_DATE,
    
    # GPS Damaged Flow
    ConversationStep.GPS_DAMAGED_LOCATION,
    ConversationStep.GPS_DAMAGED_CONTACT,
    ConversationStep.GPS_DAMAGED_INSPECTION_DATE,
    
    # Vehicle Running Flow
    ConversationStep.VEHICLE_RUNNING_DRIVER_NAME,
    ConversationStep.VEHICLE_RUNNING_DRIVER_MOBILE,
    ConversationStep.VEHICLE_RUNNING_LOCATION,
    ConversationStep.VEHICLE_RUNNING_INSPECTION_DATE,
    
    # Vehicle Standing Flow
    ConversationStep.VEHICLE_STANDING_DURATION,
    ConversationStep.VEHICLE_STANDING_LOCATION,
    ConversationStep.VEHICLE_STANDING_INSPECTION_DATE,
    
    # Other Issue Flow
    ConversationStep.OTHER_ISSUE_DESCRIPTION,
    
    # Service Request Data Collection
    ConversationStep.DATA_COLLECTION_VEHICLE_NUMBER,
    ConversationStep.DATA_COLLECTION_OWNER_NAME,
    ConversationStep.DATA_COLLECTION_OWNER_MOBILE,
    ConversationStep.DATA_COLLECTION_DRIVER_NAME,
    ConversationStep.DATA_COLLECTION_DRIVER_MOBILE,
    ConversationStep.DATA_COLLECTION_LOCATION,
    ConversationStep.DATA_COLLECTION_VEHICLE_AVAILABLE,
    ConversationStep.DATA_COLLECTION_VISIT_DATE,
    ConversationStep.DATA_COLLECTION_VISIT_TIME,
    ConversationStep.DATA_COLLECTION_ISSUE_TYPE,
    
    # Engineer Assignment
    ConversationStep.ENGINEER_ASSIGNMENT,
}

# Completion markers in context
COMPLETION_MARKERS = {
    "flow_completed",
    "case_closed",
    "service_request_created",
    "manual_review_required",
    "on_hold",
}
```

### 2. Service Engineer Flow Updates

**File**: `app/services/service_engineer_flow_service.py` (MODIFY)

**Changes Required**:

#### Change 1: Import New Helper
```python
from app.services.state_classifier import should_show_welcome, is_active_flow
```

#### Change 2: Fix No-State Handling (Lines ~541-583)

**Current Code** (Problematic):
```python
if not state or state.current_step == ConversationStep.MAIN_MENU.value:
    # ... handles numeric selection ...
    # ... handles natural language ...
    # Falls through to greeting check below
```

**New Code** (Fixed):
```python
if not state or state.current_step == ConversationStep.MAIN_MENU.value:
    # Check if it's a numeric selection (1-8)
    if normalized in ["1", "2", "3", "4", "5", "6", "7", "8"]:
        # ... existing numeric handling (unchanged) ...
    
    # Check if it's natural language (NOT a greeting)
    elif not greeting_service.is_greeting(normalized):
        # Classify and route WITHOUT welcome message
        issue_type, method = classify_customer_intent(text_body)
        
        if issue_type != "UNKNOWN":
            # Store in context
            state_manager.update_context(user.phone_number, {
                "issue_classification": issue_type,
                "classification_method": f"NLP_{method}",
                "customer_response": text_body
            })
            
            # Route directly WITHOUT welcome
            return _route_to_flow_handler(user.phone_number, issue_type, state_manager, db)
        else:
            # Unknown classification - go to OTHER flow WITHOUT welcome
            state_manager.update_context(user.phone_number, {
                "issue_classification": "UNKNOWN",
                "classification_method": "UNCLEAR",
                "customer_response": text_body,
                "clarification_needed": True
            })
            
            state_manager.set_state(user.phone_number, ConversationStep.OTHER_ISSUE_DESCRIPTION)
            
            return (
                "Samajhne ke liye kripya thoda aur detail mein batayein ki vehicle ya GPS ke saath kya issue aa raha hai.\n\n"
                "Aap normal language mein bata sakte hain."
            )
    
    # If we reach here, it's a greeting
    # Check if we should show welcome
    is_greeting = greeting_service.is_greeting(normalized)
    current_step = state.current_step if state else None
    context = state_manager.get_context(user.phone_number)
    
    if should_show_welcome(current_step, context, is_greeting):
        greeting_service.route_to_main_menu(user.phone_number)
        return greeting_service.send_welcome(user.name)
    else:
        # Greeting but has recent context - acknowledge without welcome
        return (
            "Namaste! 🙏\n\n"
            "Kripya batayein ki aap kis issue ke baare mein baat karna chahte hain?"
        )
```

#### Change 3: Remove ALL Other Welcome Calls

**Search and Replace Strategy**:
1. Find all instances of `greeting_service.send_welcome()`
2. For each instance, check if it's inside the "no-state + greeting" block
3. If not, replace with appropriate error message or clarification
4. Never call `send_welcome()` from within an active flow

**Locations to Check**:
- After general conversation handler
- After classification failure
- In error handling blocks
- In flow handler catch blocks

**Safe Replacements**:

For classification failures in active flows:
```python
# OLD (Wrong)
state_manager.clear_state(user.phone_number)
return greeting_service.send_welcome(user.name)

# NEW (Correct)
return (
    "⚠️ Kripya apna response fir se bhejen.\n"
    "⚠️ Please send your response again.\n\n"
    "Ya 'reset' type karen naye conversation ke liye.\n"
    "Or type 'reset' for a new conversation."
)
```

For errors in active flows:
```python
# OLD (Wrong)
state_manager.clear_state(user.phone_number)
return greeting_service.send_welcome(user.name)

# NEW (Correct)
return (
    "⚠️ Kuch galat ho gaya.\n"
    "⚠️ Something went wrong.\n\n"
    "Kripya apna jawab fir se bhejen ya 'reset' type karen.\n"
    "Please send your response again or type 'reset'."
)
```

### 3. Flow Completion Markers

**Files**: All flow handlers (MODIFY)

**Purpose**: Mark flows as completed so next message doesn't trigger welcome

**Implementation Pattern**:

At the end of each flow (where it currently calls `clear_state`), add completion marker:

```python
# Before clearing or resetting
state_manager.update_context(user.phone_number, {
    "flow_completed": True,
    "completion_type": "CASE_CLOSED",  # or SERVICE_REQUEST, ON_HOLD, etc.
    "completed_at": datetime.now().isoformat(),
    "completed_flow": "GPS_DAMAGED"  # or whatever flow
})

# Then set to MAIN_MENU (not clear)
state_manager.set_state(user.phone_number, ConversationStep.MAIN_MENU)
```

**Files to Update**:
- `app/services/flow_handlers/workshop_flow.py`
- `app/services/flow_handlers/accident_flow.py`
- `app/services/flow_handlers/battery_flow.py`
- `app/services/flow_handlers/gps_removed_flow.py`
- `app/services/flow_handlers/gps_damaged_flow.py`
- `app/services/flow_handlers/vehicle_running_flow.py`
- `app/services/flow_handlers/vehicle_standing_flow.py`
- `app/services/flow_handlers/other_issue_flow.py`
- `app/services/flow_handlers/service_request_collector.py`

### 4. Greeting Service Enhancement

**File**: `app/services/greeting_service.py` (MODIFY)

**Purpose**: Add context-aware greeting handling

**New Method**:

```python
def should_show_full_welcome(
    self,
    phone_number: str
) -> bool:
    """
    Determine if full welcome message should be shown.
    
    Uses state_classifier to make decision.
    
    Args:
        phone_number: User's phone number
        
    Returns:
        True if full welcome should be shown
    """
    from app.services.state_classifier import should_show_welcome
    
    state = self.state_manager.get_state(phone_number)
    context = self.state_manager.get_context(phone_number)
    current_step = state.current_step if state else None
    
    # Note: We don't know if message is greeting here
    # This function should only be called when we already know it's a greeting
    return should_show_welcome(current_step, context, is_greeting=True)

def send_acknowledgment_without_welcome(self, user_name: Optional[str]) -> str:
    """
    Acknowledge user without full welcome (for existing conversations).
    
    Args:
        user_name: User's name
        
    Returns:
        Brief acknowledgment message
    """
    display_name = user_name.strip() if user_name else "Sir/Ma'am"
    return (
        f"Namaste {display_name}! 🙏\n\n"
        "Kripya batayein ki aap kis issue ke baare mein baat karna chahte hain?"
    )
```

## Data Flow

### Flow 1: New User First Message

```
User: "Namaste"
    ↓
Check state → None
    ↓
Is greeting? → Yes
    ↓
should_show_welcome(None, {}, True) → True
    ↓
Show welcome + menu ✓
    ↓
Set state: MAIN_MENU
```

### Flow 2: User in Active Flow

```
User: "Gaadi chal rahi hai"
State: GPS_DAMAGED_LOCATION
    ↓
Check state → GPS_DAMAGED_LOCATION
    ↓
is_active_flow(GPS_DAMAGED_LOCATION) → True
    ↓
Skip welcome check entirely
    ↓
Route to gps_damaged_flow handler ✓
    ↓
State remains: GPS_DAMAGED_LOCATION (or moves to next step)
```

### Flow 3: User After Flow Completion

```
Previous flow completed: GPS_REMOVED
State: MAIN_MENU
Context: {flow_completed: true, completion_type: "SERVICE_REQUEST"}
User: "Signal nahi aa raha"
    ↓
Check state → MAIN_MENU
    ↓
Is natural language (not greeting) → Yes
    ↓
Classify intent → GPS_TECHNICAL or OTHER
    ↓
Route to flow WITHOUT welcome ✓
    ↓
Clear completion markers
    ↓
Start new flow
```

### Flow 4: Classification Failure in Active Flow

```
User: "Random text"
State: VEHICLE_RUNNING_LOCATION
    ↓
Check state → VEHICLE_RUNNING_LOCATION
    ↓
is_active_flow() → True
    ↓
Try to process in current flow
    ↓
If unclear → Ask for clarification
    ↓
NO welcome message ✓
    ↓
State remains: VEHICLE_RUNNING_LOCATION
```

### Flow 5: Side Question During Flow

```
User: "Kyu puch rahe ho?"
State: VEHICLE_STANDING_DURATION
    ↓
general_conversation_handler detects side question
    ↓
Returns answer
    ↓
NO state change
    ↓
NO welcome message ✓
    ↓
Flow continues normally
```

## Error Handling

### Strategy
- All welcome checks must be safe (handle None, missing context)
- Default to NOT showing welcome on any uncertainty
- Log all welcome decisions for debugging
- Never break flow due to welcome check failure

### Error Scenarios

**Scenario 1: State Read Failure**
```python
try:
    state = state_manager.get_state(user.phone_number)
except Exception as e:
    logger.error(f"State read failed: {e}")
    state = None
    # Proceed with None state (safer than assuming new user)
```

**Scenario 2: Context Parse Failure**
```python
try:
    context = state_manager.get_context(user.phone_number)
except Exception as e:
    logger.error(f"Context read failed: {e}")
    context = {}
    # Proceed with empty context
```

**Scenario 3: Classification Service Down**
```python
try:
    issue_type, method = classify_customer_intent(text_body)
except Exception as e:
    logger.error(f"Classification failed: {e}")
    issue_type = "UNKNOWN"
    # Route to OTHER flow without welcome
```

## Logging Strategy

### Log Levels

**INFO**: Normal flow decisions
```python
logger.info(
    f"Welcome check: {decision}",
    extra={
        "phone": user.phone_number,
        "state": current_step,
        "is_greeting": is_greeting,
        "show_welcome": result
    }
)
```

**WARNING**: Unexpected paths
```python
logger.warning(
    f"Welcome shown to active flow user",
    extra={
        "phone": user.phone_number,
        "state": current_step,
        "reason": "fallthrough"
    }
)
```

**ERROR**: Failures
```python
logger.error(
    f"Welcome check failed",
    exc_info=True,
    extra={
        "phone": user.phone_number,
        "error": str(e)
    }
)
```

## Testing Strategy

### Unit Tests

**File**: `app/tests/test_state_classifier.py` (NEW)

Test cases:
- `test_is_active_flow_with_all_flow_steps`
- `test_is_active_flow_with_main_menu`
- `test_is_active_flow_with_none`
- `test_is_completion_state`
- `test_should_show_welcome_new_user`
- `test_should_show_welcome_active_flow`
- `test_should_show_welcome_completed_flow`
- `test_should_show_welcome_no_greeting`

**File**: `app/tests/test_welcome_message_logic.py` (NEW)

Integration test cases:
- `test_new_user_greeting_shows_welcome`
- `test_active_flow_no_welcome`
- `test_completed_flow_new_intent_no_welcome`
- `test_side_question_no_welcome`
- `test_classification_failure_no_welcome`
- `test_error_recovery_no_welcome`

### Manual Test Scenarios

1. **New User Flow**
   - Send "Namaste" → Expect welcome
   - Select option → Expect flow start
   
2. **Active Flow Continuation**
   - Start GPS_DAMAGED flow
   - At location question, send "Kyu puch rahe ho?"
   - Expect answer, no welcome
   
3. **Post-Completion New Intent**
   - Complete GPS_REMOVED flow
   - Send "Signal nahi aa raha"
   - Expect new flow, no welcome
   
4. **Classification Edge Cases**
   - Start flow
   - Send gibberish
   - Expect clarification, no welcome

## Rollback Plan

### If Issues Arise

1. **Immediate Rollback**
   - Revert `service_engineer_flow_service.py` changes
   - Remove `state_classifier.py`
   - Keep flow completion markers (harmless)

2. **Partial Rollback**
   - Keep state_classifier
   - Revert service_engineer_flow_service
   - Debug in isolation

3. **Feature Flag** (Future)
   - Add config flag: `ENABLE_SMART_WELCOME`
   - Default to old behavior if false

## Performance Considerations

### Optimization Points

1. **State Checks**: All checks are in-memory, <1ms overhead
2. **Set Lookups**: Use sets for O(1) membership checks
3. **Context Access**: Single read per request (already cached)
4. **No External Calls**: All logic is local

### Performance Budget

- State classification: <5ms
- Welcome decision: <2ms
- Total overhead: <10ms (acceptable)

## Security Considerations

- No new external inputs
- No SQL injection risks (using ORM)
- No data exposure (internal state checks only)
- Logging sanitized (no PII in welcome decisions)

## Backward Compatibility

### Breaking Changes: NONE

- All existing flows continue working
- Old behavior preserved for edge cases
- New code is additive only
- No API changes

### Migration Path

1. Deploy new code (backward compatible)
2. Monitor logs for welcome decisions
3. Gradually add completion markers to flows
4. Remove old welcome calls over time

## Success Criteria

### Must Have
- ✅ No welcome message during active flows
- ✅ Welcome only for new users with greetings
- ✅ No conversation resets mid-flow
- ✅ All existing tests pass

### Should Have
- ✅ Completion markers in all flows
- ✅ Comprehensive logging
- ✅ Unit tests for new code
- ✅ Integration tests for scenarios

### Nice to Have
- 📊 Analytics on welcome suppression rate
- 📊 Metrics on conversation continuity
- 🔧 Feature flag for gradual rollout

## Future Enhancements

1. **Session Timeout**: Add time-based session expiry
2. **Context Pruning**: Clean old completion markers
3. **Smart Resume**: "Continue from where you left off?"
4. **Analytics**: Track welcome appropriateness metrics
5. **A/B Testing**: Experiment with different acknowledgments
