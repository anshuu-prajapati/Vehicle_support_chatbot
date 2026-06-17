# Clarification Handler - Integration Example

## Quick Integration Guide

This document shows **exactly how** to integrate the clarification handler into your existing flow handlers.

---

## Step-by-Step Integration

### Step 1: Import at Top of File

Add these imports at the top of your flow handler file:

```python
from app.services.clarification_handler import (
    should_clarify,
    generate_clarification_response,
    get_context_explanation_for_step,
    get_current_question_text
)
```

---

### Step 2: Add Check at Start of Handler Function

Add this code **immediately after** getting context and **before** any processing:

```python
def handle_your_flow(user_phone, text_body, current_step, state_manager, db):
    """Your flow handler"""
    
    context = state_manager.get_context(user_phone)
    your_sub_step = context.get("your_sub_step_key")
    
    # ========== ADD THIS BLOCK ==========
    # Check if user needs clarification
    if should_clarify(text_body):
        logger.info(f"User needs clarification at step {current_step}, sub_step {your_sub_step}")
        
        # Get context explanation and current question
        context_explanation = get_context_explanation_for_step(current_step, your_sub_step)
        current_question = get_current_question_text(current_step, your_sub_step)
        
        # Generate and return clarification WITHOUT changing state
        clarification = generate_clarification_response(
            user_message=text_body,
            current_question=current_question,
            context_explanation=context_explanation
        )
        
        return clarification
    # ========== END OF ADDITION ==========
    
    # Your existing code continues below
    if current_step == ...:
        ...
```

---

## Complete Example: GPS Damaged Flow

Here's the **complete code** showing integration:

```python
"""
GPS Damaged Flow Handler with Clarification Support
"""
import logging
from datetime import datetime, date
from sqlalchemy.orm import Session

from app.services.state_manager import StateManager, ConversationStep
from app.services.ticket_service import create_service_request_ticket

# ADD THESE IMPORTS
from app.services.clarification_handler import (
    should_clarify,
    generate_clarification_response,
    get_context_explanation_for_step,
    get_current_question_text
)

logger = logging.getLogger("app.gps_damaged_flow")


def handle_gps_damaged_flow(
    user_phone: str,
    text_body: str,
    current_step: str,
    state_manager: StateManager,
    db: Session
) -> str:
    """
    Handle GPS Damaged flow with LLM-driven conversational understanding.
    """
    context = state_manager.get_context(user_phone)
    gps_sub_step = context.get("gps_damaged_sub_step")
    
    logger.info(
        f"GPS Damaged Flow: Processing",
        extra={
            "phone": user_phone,
            "step": current_step,
            "sub_step": gps_sub_step,
            "message": text_body[:50]
        }
    )
    
    # ========== CLARIFICATION CHECK (ADD THIS) ==========
    if should_clarify(text_body):
        logger.info(f"GPS Damaged: User needs clarification at sub_step {gps_sub_step}")
        
        context_explanation = get_context_explanation_for_step(
            current_step, 
            gps_sub_step
        )
        current_question = get_current_question_text(
            current_step, 
            gps_sub_step
        )
        
        clarification = generate_clarification_response(
            user_message=text_body,
            current_question=current_question,
            context_explanation=context_explanation
        )
        
        return clarification
    # ========== END CLARIFICATION CHECK ==========
    
    # Existing flow logic continues unchanged
    if current_step == ConversationStep.GPS_DAMAGED_LOCATION.value:
        
        # Q2 (after NO): Expected date
        if gps_sub_step == GPS_DAMAGED_EXPECTED_DATE:
            if _user_changed_mind_wants_service(text_body):
                # ... existing code ...
            
            parsed_date, error = _validate_date(text_body)
            # ... rest of existing code ...
        
        # Q3: Visit date/time
        if gps_sub_step == GPS_DAMAGED_VISIT_DATETIME:
            # ... existing code ...
        
        # Q4: Contact confirmation
        if gps_sub_step == GPS_DAMAGED_CONTACT_CONFIRM:
            # ... existing code ...
        
        # ... rest of your existing flow logic ...
```

---

## What This Changes

### User Experience BEFORE:
```
Bot: "Kya aap GPS installation ke liye service request continue karna chahte hain?"
User: "Mujhe samajh nahi aaya"
Bot: [Treats as NO answer] ❌
     "Theek hai, expected date batayein..."
```

### User Experience AFTER:
```
Bot: "Kya aap GPS installation ke liye service request continue karna chahte hain?"
User: "Mujhe samajh nahi aaya"
Bot: [Detects confusion] ✅
     "Koi baat nahi. 😊
      Mera matlab hai: Hum GPS device ko dobara lagwane ke liye service engineer arrange kar sakte hain.
      Kya aap GPS installation ki process aage badhana chahte hain?"

[User can now answer properly]
[Workflow stays on SAME step]
```

---

## Testing After Integration

### Test 1: User Asks Question
```python
# Scenario
bot_asks = "Vehicle inspection ke liye kab available rahegi?"
user_says = "Kyun pooch rahe ho?"

# Expected behavior
# - should_clarify() returns True
# - Bot explains: "Hum service engineer ki visit schedule karne ke liye..."
# - Bot re-asks same question
# - State UNCHANGED
```

### Test 2: User Confused
```python
# Scenario
bot_asks = "Kya aap GPS installation ke liye service request continue karna chahte hain?"
user_says = "Mujhe samajh nahi aaya"

# Expected behavior
# - should_clarify() returns True
# - Bot explains what GPS installation means
# - Bot re-asks same question
# - State UNCHANGED
```

### Test 3: User Answers Normally
```python
# Scenario
bot_asks = "Vehicle inspection ke liye kab available rahegi?"
user_says = "Kal subah"

# Expected behavior
# - should_clarify() returns False
# - Bot processes answer normally
# - Bot moves to NEXT step
# - State CHANGES (normal flow)
```

---

## Quick Copy-Paste Template

Copy this and modify for your flow:

```python
# At top of file
from app.services.clarification_handler import (
    should_clarify,
    generate_clarification_response,
    get_context_explanation_for_step,
    get_current_question_text
)

# In your flow handler function, after getting context
context = state_manager.get_context(user_phone)
your_sub_step = context.get("your_sub_step_key")

# Add clarification check
if should_clarify(text_body):
    logger.info(f"User needs clarification at {current_step}, {your_sub_step}")
    
    context_explanation = get_context_explanation_for_step(current_step, your_sub_step)
    current_question = get_current_question_text(current_step, your_sub_step)
    
    clarification = generate_clarification_response(
        user_message=text_body,
        current_question=current_question,
        context_explanation=context_explanation
    )
    
    return clarification

# Your existing code continues...
```

---

## Important Rules

✅ **DO:**
- Add check BEFORE any answer processing
- Return clarification WITHOUT changing state
- Log when clarification is provided

❌ **DON'T:**
- Skip the clarification check
- Change conversation state during clarification
- Remove existing flow logic

---

## Integration Order (Suggested)

1. **GPS Damaged Flow** (Complex, has sub-steps)
2. **Vehicle Running Flow** (Similar pattern)
3. **GPS Removed Flow** (Similar pattern)
4. **Workshop Flow** (Simpler)
5. **Accident Flow** (Simpler)
6. **Battery Flow** (Simpler)
7. Other flows as needed

---

## Success Criteria

After integration, test these phrases at ANY step:

- "Mujhe samajh nahi aaya" → Should clarify
- "Kya matlab?" → Should clarify
- "Kyun pooch rahe ho?" → Should explain
- "Thoda aur batao" → Should clarify
- "Haan" → Should process normally
- "Kal subah" → Should process normally

---

**Status:** READY FOR INTEGRATION ✅
**Time Required:** 5 minutes per flow
**Complexity:** LOW (Copy-paste + test)
