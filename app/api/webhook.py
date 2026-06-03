# from fastapi import APIRouter
# from fastapi import Request

# from app.core.config import VERIFY_TOKEN

# from app.services.rag_service import ask_question
# from app.services.whatsapp_service import send_whatsapp_message

# router = APIRouter(
#     prefix="/webhook",
#     tags=["WhatsApp"]
# )


# @router.get("/")
# def verify_webhook(
#     hub_mode: str = None,
#     hub_verify_token: str = None,
#     hub_challenge: str = None
# ):

#     if hub_verify_token == VERIFY_TOKEN:
#         return int(hub_challenge)

#     return {
#         "error": "Verification failed"
#     }


# @router.post("/")
# async def receive_message(request: Request):

#     body = await request.json()

#     print(body)

#     try:

#         value = body["entry"][0]["changes"][0]["value"]

#         if "messages" not in value:
#             return {"status": "ignored"}
        
#         message = value["messages"][0]

#         sender = message["from"]

#         text = message["text"]["body"]

#         print("Sender:", sender)
#         print("Message:", text)

#         from app.services.whatsapp_service import send_whatsapp_message

#         result = ask_question(text)

#         answer = f"""
#         Problem: {result['problem']}
#         Description:
#         {result['description']}
        
#         Solutions:
        
#         """
        
#         for i, solution in enumerate(
#             result["solutions"],
#             start=1
#         ):
#             answer += f"{i}. {solution}\n"
        
#         send_whatsapp_message(
#             sender,
#             answer
#         )

#     except Exception as e:
#         print("ERROR:", e)

#     return {"status": "ok"}



















import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import VERIFY_TOKEN
from app.services.support_flow_service import handle_support_message
from app.services.chat_service import save_chat
from app.services.user_service import get_or_create_user
from app.services.whatsapp_service import send_whatsapp_message

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/webhook",
    tags=["WhatsApp"]
)


def _normalize_name(name: str, phone_number: str) -> str:
    if not name or name == phone_number:
        return "sir/ma'am"
    return name


@router.get("/")
def verify_webhook(
    hub_mode: str = None,
    hub_verify_token: str = None,
    hub_challenge: str = None
):
    logger.info("Webhook verification request: mode=%s, token=%s, challenge=%s", 
               hub_mode, "***" if hub_verify_token else None, "***" if hub_challenge else None)
    
    if not VERIFY_TOKEN:
        logger.error("VERIFY_TOKEN not configured! Check environment variables.")
        return {"error": "Verification token not configured"}
    
    if hub_verify_token == VERIFY_TOKEN:
        logger.info("✓ Webhook verified successfully")
        return int(hub_challenge)

    logger.error("✗ Webhook verification failed: token mismatch")
    return {"error": "Verification failed"}


@router.post("/")
async def receive_message(request: Request):
    print("\n" + "="*80)
    print("📨 WEBHOOK POST REQUEST RECEIVED")
    print("="*80)
    
    raw_body = await request.body()
    print(f"Body length: {len(raw_body)} bytes")
    
    if not raw_body:
        logger.warning("Webhook received empty body")
        print("❌ Empty body!")
        return JSONResponse(status_code=400, content={"status": "ignored", "detail": "empty body"})

    try:
        body = json.loads(raw_body)
        print(f"✓ JSON parsed successfully")
    except json.JSONDecodeError as e:
        logger.warning("Webhook received invalid JSON: %s", e)
        print(f"❌ JSON parsing error: {e}")
        return JSONResponse(status_code=400, content={"status": "ignored", "detail": "invalid JSON"})

    logger.debug("Webhook body: %s", body)
    print(f"Body: {json.dumps(body, indent=2)[:500]}...")

    try:
        entry = body.get("entry")
        if not entry or not isinstance(entry, list):
            logger.debug("No entry in webhook")
            print("❌ No entry in webhook")
            return {"status": "ignored"}

        print(f"✓ Found {len(entry)} entries")
        
        changes = entry[0].get("changes") if entry[0] else None
        if not changes or not isinstance(changes, list):
            logger.debug("No changes in webhook entry")
            print("❌ No changes in entry")
            return {"status": "ignored"}

        print(f"✓ Found {len(changes)} changes")

        value = changes[0].get("value")
        if not value:
            logger.debug("No value in webhook changes")
            print("❌ No value in changes")
            return {"status": "ignored"}
        
        if "messages" not in value:
            logger.debug("No messages in webhook value, checking for status updates...")
            print(f"No messages found. Value keys: {list(value.keys())}")
            return {"status": "ignored"}

        print(f"✓ Found messages in value")
        message = value["messages"][0]
        sender = message.get("from")
        text_body = message.get("text", {}).get("body")

        print(f"Sender: {sender}")
        print(f"Text: {text_body}")

        if not sender or not text_body:
            logger.warning("Missing sender or text_body in message")
            print(f"❌ Missing sender={bool(sender)} or text_body={bool(text_body)}")
            return {"status": "ignored"}

        logger.info("✓ Received WhatsApp message from %s: %s", sender, text_body)
        print(f"✓ Processing message...")

        user = get_or_create_user(sender)
        logger.debug("User retrieved/created: %s", user.phone_number)
        print(f"✓ User: {user.phone_number}")
        
        answer = handle_support_message(user, text_body)
        logger.debug("Generated response: %s", answer[:100] if len(answer) > 100 else answer)
        print(f"✓ Response generated: {answer[:100]}...")
        
        success = send_whatsapp_message(user.phone_number, answer)
        print(f"Message send result: {success}")
        
        if not success:
            logger.error("Failed to send WhatsApp message to %s", user.phone_number)
            print(f"❌ Failed to send message!")
            return JSONResponse(status_code=500, content={"status": "error", "detail": "failed to send message"})
        
        save_chat(user.phone_number, text_body, answer)
        logger.info("Chat saved for user %s", user.phone_number)
        print(f"✓ Chat saved")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.exception("Webhook processing failed")
        print(f"❌ EXCEPTION: {str(e)}")
        import traceback
        print(traceback.format_exc())
        print("="*80 + "\n")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})

    return {"status": "ok"}
