# Vehicle API - WhatsApp Flow Integration Guide

## Overview

This guide shows how to integrate the Vehicle API with your existing WhatsApp conversation flow.

## Integration Points

### 1. Vehicle Number Input State

When user enters vehicle number in the conversation flow, validate it against the Vehicle API.

### Current Flow (Before Integration)

```python
# app/services/support_flow_service.py

if current_step == ConversationStep.VEHICLE_NUMBER.value:
    state_manager.update_context(user.phone_number, {"vehicle_number": text_body})
    state_manager.set_state(user.phone_number, ConversationStep.ASK_DRIVER_AVAILABILITY)
    return (
        "Kripya driver vehicle ke paas hai?\n"
        "1️⃣ Haan\n"
        "2️⃣ Nahi"
    )
```

### Enhanced Flow (With Vehicle API)

```python
# app/services/support_flow_service.py

if current_step == ConversationStep.VEHICLE_NUMBER.value:
    # Import vehicle integration
    from app.services.vehicle_whatsapp_integration import VehicleWhatsAppIntegration
    
    # Validate vehicle
    vehicle_integration = VehicleWhatsAppIntegration()
    is_valid, message, vehicle_details = await vehicle_integration.validate_and_fetch_vehicle(text_body)
    
    if not is_valid:
        # Vehicle not found or error
        await vehicle_integration.close()
        return message
    
    # Vehicle found - store in context
    vehicle_context = vehicle_integration.format_vehicle_summary_for_context(vehicle_details)
    state_manager.update_context(user.phone_number, vehicle_context)
    
    # Close integration
    await vehicle_integration.close()
    
    # Send vehicle details message
    # Then proceed to next step
    state_manager.set_state(user.phone_number, ConversationStep.ASK_DRIVER_AVAILABILITY)
    
    return (
        f"{message}\n\n"
        "Kripya driver vehicle ke paas hai?\n"
        "1️⃣ Haan\n"
        "2️⃣ Nahi"
    )
```

## Complete Integration Example

### Step 1: Update support_flow_service.py

```python
# Add at the top of the file
from app.services.vehicle_whatsapp_integration import VehicleWhatsAppIntegration

# Modify the vehicle number handler
async def handle_vehicle_number_input(
    user,
    text_body: str,
    state_manager: StateManager
) -> str:
    """
    Handle vehicle number input with API validation
    """
    vehicle_integration = VehicleWhatsAppIntegration()
    
    try:
        # Validate and fetch vehicle details
        is_valid, message, vehicle_details = await vehicle_integration.validate_and_fetch_vehicle(text_body)
        
        if not is_valid:
            # Vehicle not found - ask user to retry
            logger.warning(
                "Invalid vehicle number entered",
                extra={"phone_number": user.phone_number, "vehicle_number": text_body}
            )
            return message
        
        # Vehicle found - store comprehensive context
        vehicle_context = vehicle_integration.format_vehicle_summary_for_context(vehicle_details)
        state_manager.update_context(user.phone_number, vehicle_context)
        
        # Log successful validation
        logger.info(
            "Vehicle validated successfully",
            extra={
                "phone_number": user.phone_number,
                "vehicle_number": vehicle_details.vehicle_number,
                "status": vehicle_details.status.value,
            }
        )
        
        # Move to next step
        state_manager.set_state(user.phone_number, ConversationStep.ASK_DRIVER_AVAILABILITY)
        
        # Return combined message
        return (
            f"{message}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Kripya driver vehicle ke paas hai?\n"
            "1️⃣ Haan\n"
            "2️⃣ Nahi"
        )
        
    except Exception as e:
        logger.error(
            "Error validating vehicle",
            extra={"phone_number": user.phone_number, "error": str(e)}
        )
        return (
            "⚠️ Vehicle ki jaankari lene mein problem aa rahi hai.\n"
            "Kripya thodi der baad dobara try karein."
        )
    finally:
        await vehicle_integration.close()
```

### Step 2: Update webhook.py to support async

```python
# app/api/webhook.py

@router.post("/")
async def receive_message(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    sender = None

    try:
        # ... existing validation code ...
        
        user = get_or_create_user(sender, db=db)
        state_manager = StateManager(db)
        
        # Call async handler
        answer = await handle_support_message(user, text_body, state_manager)
        
        send_whatsapp_message(user.phone_number, answer)
        save_chat(user.phone_number, text_body, answer)
        
    except Exception as exc:
        logger.exception("Unexpected error processing webhook", exc_info=exc)
        if sender:
            try:
                send_whatsapp_message(sender, TECHNICAL_ERROR_MESSAGE)
            except Exception:
                logger.exception("Failed to send technical error message to sender")
        return {"status": "error", "detail": str(exc)}

    return {"status": "ok"}
```

### Step 3: Update support_flow_service.py main handler

```python
# Make the main handler async
async def handle_support_message(user, text_body: str, state_manager: StateManager) -> str:
    normalized = _normalize_text(text_body)
    greeting_service = GreetingService(state_manager)
    menu_service = MenuService(state_manager)

    # ... existing greeting and state checks ...

    # Handle vehicle number input
    if current_step == ConversationStep.VEHICLE_NUMBER.value:
        return await handle_vehicle_number_input(user, text_body, state_manager)

    # ... rest of the existing handlers ...
```

## Menu Integration

### Add "Check Vehicle Status" Option

```python
# app/services/menu_service.py

def get_main_menu_text(self, user_name: str) -> str:
    return (
        f"Namaste {user_name}! 🙏\n\n"
        "Main Menu:\n"
        "1️⃣ Vehicle Problem Report\n"
        "2️⃣ Check Vehicle Status\n"
        "3️⃣ Not Working Vehicles List\n"
        "4️⃣ Engineer Request\n"
        "5️⃣ Help\n\n"
        "Kripya option select karein."
    )

async def handle_menu_selection(self, phone_number: str, selection: str) -> str:
    normalized = selection.strip().lower()
    
    if normalized in ["1", "vehicle problem", "problem"]:
        self.state_manager.set_state(phone_number, ConversationStep.VEHICLE_NUMBER)
        return "Kripya vehicle number bhejiye."
    
    elif normalized in ["2", "check status", "status"]:
        self.state_manager.set_state(phone_number, ConversationStep.VEHICLE_NUMBER)
        return "Kripya vehicle number bhejiye jiska status check karna hai."
    
    elif normalized in ["3", "not working", "list"]:
        # Show not working vehicles
        from app.services.vehicle_whatsapp_integration import VehicleWhatsAppIntegration
        vehicle_integration = VehicleWhatsAppIntegration()
        try:
            message = await vehicle_integration.get_not_working_vehicles_message()
            return message
        finally:
            await vehicle_integration.close()
    
    # ... rest of menu options ...
```

## Context Storage

### Vehicle Context Structure

When a vehicle is validated, the following context is stored:

```python
{
    "vehicle_number": "DL01AB1234",
    "vehicle_status": "NOT_WORKING",
    "vehicle_imei": "123456789012345",
    "vehicle_owner_name": "John Doe",
    "vehicle_owner_phone": "9876543210",
    "vehicle_driver_name": "Driver Name",
    "vehicle_driver_phone": "9876543211",
    "vehicle_last_location": "Delhi NCR",
    "vehicle_last_update": "2024-01-15T10:30:00"
}
```

### Accessing Vehicle Context

```python
# Get vehicle context
context = state_manager.get_context(phone_number)

vehicle_number = context.get("vehicle_number")
vehicle_status = context.get("vehicle_status")
vehicle_location = context.get("vehicle_last_location")

# Use in troubleshooting flow
if vehicle_status == "NOT_WORKING":
    # Start troubleshooting
    pass
elif vehicle_status == "OFFLINE":
    # Check connectivity
    pass
```

## Conversation Flow Examples

### Example 1: Vehicle Found - Not Working

```
User: DL01AB1234

Bot: ✅ Vehicle Mil Gaya!
📋 Vehicle Number: DL01AB1234
⚠️ Status: Kaam Nahi Kar Raha
📍 Last Location: Delhi NCR
👤 Owner: John Doe
🕐 Last Update: 15-01-2024 10:30

⚠️ Yeh vehicle kaam nahi kar raha hai.

Kya aap troubleshooting start karna chahenge?
1️⃣ Haan
2️⃣ Nahi

━━━━━━━━━━━━━━━━━━━━

Kripya driver vehicle ke paas hai?
1️⃣ Haan
2️⃣ Nahi
```

### Example 2: Vehicle Found - Online

```
User: DL02CD5678

Bot: ✅ Vehicle Mil Gaya!
📋 Vehicle Number: DL02CD5678
🟢 Status: Online
📍 Last Location: Mumbai
👤 Owner: Jane Smith
🕐 Last Update: 15-01-2024 11:00

✅ Vehicle online hai aur kaam kar raha hai.

Kya aapko koi aur madad chahiye?
1️⃣ Haan
2️⃣ Nahi

━━━━━━━━━━━━━━━━━━━━

Kripya driver vehicle ke paas hai?
1️⃣ Haan
2️⃣ Nahi
```

### Example 3: Vehicle Not Found

```
User: INVALID123

Bot: ❌ Vehicle INVALID123 nahi mila.

Kripya vehicle number dobara check karein aur phir se bhejein.
```

### Example 4: Not Working Vehicles List

```
User: 3

Bot: ⚠️ Total 5 vehicles NOT WORKING hain:

1. DL01AB1234 - John Doe
2. DL02CD5678 - Jane Smith
3. DL03EF9012 - Bob Johnson
4. MH01GH3456 - Alice Brown
5. KA01IJ7890 - Charlie Davis

Kisi vehicle ki details dekhne ke liye vehicle number bhejein.
```

## Error Handling

### Network Errors

```python
try:
    vehicle_integration = VehicleWhatsAppIntegration()
    is_valid, message, vehicle = await vehicle_integration.validate_and_fetch_vehicle(vehicle_number)
except Exception as e:
    logger.error("Vehicle API error", extra={"error": str(e)})
    return (
        "⚠️ Vehicle ki jaankari lene mein problem aa rahi hai.\n"
        "Kripya thodi der baad dobara try karein."
    )
finally:
    await vehicle_integration.close()
```

### Timeout Handling

```python
# Timeout is handled automatically by the client
# Default: 30 seconds
# Configure via VEHICLE_API_TIMEOUT environment variable
```

## Performance Considerations

### 1. Connection Reuse

```python
# DON'T: Create new integration for each request
for vehicle in vehicles:
    integration = VehicleWhatsAppIntegration()
    await integration.validate_and_fetch_vehicle(vehicle)
    await integration.close()

# DO: Reuse integration instance
integration = VehicleWhatsAppIntegration()
try:
    for vehicle in vehicles:
        await integration.validate_and_fetch_vehicle(vehicle)
finally:
    await integration.close()
```

### 2. Enable Caching

```bash
# .env
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
VEHICLE_CACHE_TTL=300  # 5 minutes
```

### 3. Async Operations

Always use `await` for vehicle operations to avoid blocking:

```python
# Correct
answer = await handle_support_message(user, text_body, state_manager)

# Incorrect (will block)
answer = handle_support_message(user, text_body, state_manager)
```

## Testing Integration

### Manual Testing

```bash
# 1. Start the server
uvicorn app.main:app --reload

# 2. Test vehicle endpoint
curl http://localhost:8000/vehicles/DL01AB1234

# 3. Test health check
curl http://localhost:8000/vehicles/health

# 4. Test not working vehicles
curl http://localhost:8000/vehicles/not-working
```

### WhatsApp Testing

1. Send vehicle number via WhatsApp
2. Verify vehicle details are fetched
3. Check conversation context is updated
4. Verify flow continues correctly

## Monitoring

### Key Metrics

```python
# Log vehicle validations
logger.info(
    "Vehicle validated",
    extra={
        "vehicle_number": vehicle_number,
        "status": vehicle_status,
        "response_time_ms": response_time,
    }
)

# Log validation failures
logger.warning(
    "Vehicle not found",
    extra={
        "vehicle_number": vehicle_number,
        "user_phone": phone_number,
    }
)
```

### Dashboard Queries

```sql
-- Count vehicle validations per day
SELECT DATE(timestamp), COUNT(*) 
FROM logs 
WHERE message = 'Vehicle validated'
GROUP BY DATE(timestamp);

-- Most checked vehicles
SELECT vehicle_number, COUNT(*) as checks
FROM logs
WHERE message = 'Vehicle validated'
GROUP BY vehicle_number
ORDER BY checks DESC
LIMIT 10;
```

## Rollback Plan

If issues occur, you can disable vehicle API integration:

```python
# Add feature flag
USE_VEHICLE_API = os.getenv("USE_VEHICLE_API", "true").lower() == "true"

if USE_VEHICLE_API:
    # Use vehicle API
    vehicle_integration = VehicleWhatsAppIntegration()
    is_valid, message, vehicle = await vehicle_integration.validate_and_fetch_vehicle(text_body)
else:
    # Fallback to old flow
    state_manager.update_context(user.phone_number, {"vehicle_number": text_body})
    return "Vehicle number saved. Proceeding..."
```

## Next Steps

1. ✅ Deploy vehicle API integration
2. ✅ Test with real vehicle numbers
3. ✅ Monitor error rates
4. ✅ Enable Redis caching
5. ✅ Add analytics dashboard
6. ✅ Implement webhooks for real-time updates

## Support

For issues:
1. Check `/vehicles/health` endpoint
2. Review application logs
3. Verify environment variables
4. Test external API connectivity
