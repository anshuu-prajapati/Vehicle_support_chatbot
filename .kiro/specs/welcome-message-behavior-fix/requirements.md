# Welcome Message Behavior Fix - Requirements

## Problem Statement

The chatbot currently sends the welcome message "Namaste Sir 👋 Main GPS Support Assistant hoon." inappropriately during active conversations, causing:
- Conversation resets when users send unexpected responses
- Poor user experience when intent classification fails
- Loss of conversation context mid-flow
- Confusion for users who are already engaged in a conversation

## User Stories

### Story 1: Active Flow Continuation
**As a** customer currently in an active conversation flow  
**I want** the bot to remember my context and continue the conversation  
**So that** I don't have to restart my conversation when I ask side questions or send unexpected responses

**Acceptance Criteria:**
- When user is in any active flow (GPS_DAMAGED_LOCATION, VEHICLE_RUNNING_LOCATION, etc.)
- And user sends any message (including unexpected text, side questions, delays)
- Then bot should NOT show welcome message
- And bot should continue within the current flow context
- And conversation state should be preserved

### Story 2: New User Welcome
**As a** new user starting a conversation  
**I want** to receive a friendly welcome message with options  
**So that** I understand what help is available

**Acceptance Criteria:**
- When user has NO conversation state
- And user sends a greeting message (namaste, hello, hi)
- Then bot should show welcome message
- And bot should display main menu options
- And conversation state should be set to MAIN_MENU

### Story 3: Post-Completion New Intent
**As a** customer who just completed a flow  
**I want** to report a new issue without seeing the welcome message again  
**So that** the conversation feels natural and continuous

**Acceptance Criteria:**
- When user has completed a flow (Case Closed, Service Request Created, On Hold)
- And conversation state is marked as completed
- And user sends a new message with a new issue
- Then bot should classify the new intent directly
- And bot should start the appropriate flow WITHOUT welcome message
- And bot should NOT show main menu again

### Story 4: Classification Failure Handling
**As a** customer in an active conversation  
**I want** the bot to handle unclear responses gracefully  
**So that** I don't lose my conversation context

**Acceptance Criteria:**
- When user is in an active flow
- And intent classification fails or returns UNKNOWN
- Then bot should ask for clarification within the current flow
- And bot should NOT show welcome message
- And bot should NOT reset conversation state
- And bot should remember all collected information

### Story 5: Side Questions During Flow
**As a** customer answering flow questions  
**I want** to ask side questions (like "why are you asking this?")  
**So that** I can get clarification without losing my place

**Acceptance Criteria:**
- When user is in an active flow
- And user asks a side question (handled by general_conversation_handler)
- Then bot should answer the side question
- And bot should NOT show welcome message
- And bot should NOT reset conversation state
- And bot should return to the same step after answering

## Current Behavior (Problematic)

### Scenario 1: During Active Flow
```
State: GPS_DAMAGED_LOCATION
User: "Gaadi chal rahi hai"
Bot: "Namaste Sir 👋 Main GPS Support Assistant hoon..." ❌ WRONG
```

### Scenario 2: Side Question
```
State: VEHICLE_RUNNING_LOCATION  
User: "Kyu puch rahe ho?"
Bot: "Namaste Sir 👋 Main GPS Support Assistant hoon..." ❌ WRONG
```

### Scenario 3: After Completion
```
Previous Flow: GPS_REMOVED (completed)
User: "Signal nahi aa raha"
Bot: "Namaste Sir 👋 Main GPS Support Assistant hoon..." ❌ WRONG
```

## Expected Behavior (Correct)

### Scenario 1: During Active Flow
```
State: GPS_DAMAGED_LOCATION
User: "Gaadi chal rahi hai"
Bot: Processes response within current flow, asks follow-up ✓ CORRECT
```

### Scenario 2: Side Question
```
State: VEHICLE_RUNNING_LOCATION  
User: "Kyu puch rahe ho?"
Bot: Answers question, then continues asking for location ✓ CORRECT
```

### Scenario 3: After Completion
```
Previous Flow: GPS_REMOVED (completed)
User: "Signal nahi aa raha"
Bot: Classifies as GPS_TECHNICAL, starts appropriate flow ✓ CORRECT
```

### Scenario 4: New User Greeting
```
State: None
User: "Namaste"
Bot: "Namaste Sir 👋 Main GPS Support Assistant hoon..." ✓ CORRECT
```

## Business Rules

### Rule 1: Welcome Message Triggers (ONLY)
Welcome message should ONLY be shown when:
1. **New Conversation**: No conversation state exists AND user sends a greeting
2. **Explicit Reset**: User explicitly types "reset", "start over", "new request"
3. **Session Expired**: Conversation timeout reached (if implemented)

### Rule 2: Never Show Welcome When
Welcome message should NEVER be shown when:
1. **Active Flow**: User is in any active conversation step
2. **Side Questions**: User asks clarification questions during flow
3. **Unexpected Text**: User sends non-standard responses during flow
4. **Classification Fails**: Intent classification returns UNKNOWN during active flow
5. **After Completion**: User sends new message after completing a previous flow
6. **Error Handling**: Any error occurs during an active flow
7. **Delay/Hold Responses**: User says "abhi nahi", "pata nahi", "baad mein"

### Rule 3: Active Flow Principle
If conversation state exists and is NOT at MAIN_MENU or completion state:
- Continue the current flow
- Preserve all context and collected data
- Handle unexpected responses within the flow
- Never restart or show welcome message

### Rule 4: Completion States
These states indicate a completed flow:
- Case Closed (Workshop, Accident, Battery flows)
- Service Request Created (GPS Removed, GPS Damaged, Vehicle Running, Vehicle Standing)
- Manual Review Required (Other flow)
- On Hold (Delay/hold handler)

After these states:
- Mark conversation as completed
- Next message should classify new intent WITHOUT welcome
- Only show welcome if it's explicitly a greeting from fresh context

### Rule 5: Human-Like Behavior
The bot should behave like a human support executive:
- Remember conversation context
- Continue naturally without restarting
- Handle side questions gracefully
- Never greet the same person multiple times in one session

## Technical Requirements

### TR1: State Detection Enhancement
- Add function to detect if conversation state represents "active flow"
- Active flow = any state except MAIN_MENU, None, and completion markers
- Add function to detect if conversation was "recently completed"

### TR2: Welcome Message Guard
- Add guard function that checks:
  - Is state active? → NO welcome
  - Is it a greeting + no state? → YES welcome
  - Is it a greeting + completed state? → NO welcome, process new intent
  - Did classification fail + active state? → NO welcome, ask for clarification

### TR3: Greeting Detection Update
- Update `greeting_service.py` to distinguish between:
  - New user greeting (no state) → Show welcome
  - Existing user greeting (has state) → Acknowledge without welcome

### TR4: Flow Completion Markers
- Add context flag: `flow_completed: true` when flows finish
- Add context field: `completion_type: "CASE_CLOSED" | "SERVICE_REQUEST" | "ON_HOLD" | "MANUAL_REVIEW"`
- Use these markers to handle next message appropriately

### TR5: Classification Failure Handling
- When classification returns UNKNOWN:
  - Check if active flow exists
  - If yes: Route to clarification within current flow
  - If no: Route to OTHER flow without welcome
  - Never show welcome message

## Edge Cases

### Edge Case 1: Rapid Message Changes
```
User sends: "GPS removed" → Flow starts
User immediately sends: "No wait, actually battery issue"
Expected: Reclassify and switch flow, no welcome
```

### Edge Case 2: Multiple Delays
```
User: "Abhi nahi karana" → Marked ON_HOLD
User: "Abhi bhi nahi" → Stay ON_HOLD, no welcome
User: "Okay ab kar lo" → Resume or restart flow, no welcome
```

### Edge Case 3: Error Recovery
```
System error occurs during flow
Expected: Apologize, keep context, allow retry, no welcome
```

### Edge Case 4: Long Pause
```
User starts flow → Disappears for hours → Returns
Expected: Resume from last step, no welcome
(Future: Could add session timeout logic)
```

## Success Metrics

1. **Zero inappropriate welcomes**: Welcome message only appears for new conversations
2. **Context preservation**: No conversation resets during active flows
3. **User satisfaction**: Natural conversation flow without repetitive greetings
4. **Error reduction**: Fewer confusion-related support escalations

## Non-Functional Requirements

- **Performance**: Welcome check should add <10ms to response time
- **Reliability**: All state checks must be safe and handle null/missing data
- **Logging**: Log all welcome message decisions for debugging
- **Backward Compatibility**: Existing flows should continue working
- **Testing**: All scenarios must have test cases

## Out of Scope

- Session timeout implementation (future enhancement)
- Multi-channel support (email, voice)
- Conversation history review feature
- Analytics dashboard for conversation flows

## Dependencies

- Existing state_manager.py (ConversationStep enum)
- Existing greeting_service.py (is_greeting, send_welcome)
- Existing general_conversation_handler.py (side question handling)
- Existing delay_and_hold_handler.py (delay/hold detection)
- All flow handlers (must continue working unchanged)

## Assumptions

1. conversation_state table accurately tracks current step
2. All flows properly set and update conversation state
3. Context JSON is properly maintained across steps
4. general_conversation_handler is called before flow routing
5. delay_and_hold_handler is integrated in all flows
