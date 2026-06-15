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



















import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import VERIFY_TOKEN
from app.db.dependencies import get_db
from app.services.state_manager import StateManager
from app.services.support_flow_service import handle_support_message
from app.services.chat_service import save_chat
from app.services.user_service import get_or_create_user
from app.services.whatsapp_service import send_whatsapp_message

router = APIRouter(
    prefix="/webhook",
    tags=["WhatsApp"]
)

logger = logging.getLogger("app.webhook")

TECHNICAL_ERROR_MESSAGE = (
    "Maaf kijiye, kuch technical issue aa gaya hai.\n"
    "Kripya dobara try kare."
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
    if hub_verify_token == VERIFY_TOKEN:
        return int(hub_challenge)

    return {
        "error": "Verification failed"
    }


@router.post("/")
async def receive_message(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    sender = None

    try:
        entry = body.get("entry")
        if not entry or not isinstance(entry, list):
            logger.debug("Webhook ignored because entry was missing or invalid", extra={"body": body})
            return {"status": "ignored"}

        changes = entry[0].get("changes") if entry[0] else None
        if not changes or not isinstance(changes, list):
            logger.debug("Webhook ignored because changes were missing or invalid", extra={"body": body})
            return {"status": "ignored"}

        value = changes[0].get("value")
        if not value or "messages" not in value:
            logger.debug("Webhook ignored because no messages were present", extra={"body": body})
            return {"status": "ignored"}

        message = value["messages"][0]
        sender = message.get("from")
        text_body = message.get("text", {}).get("body")

        if not sender or not text_body:
            logger.debug("Webhook ignored because sender or text was missing", extra={"message": message})
            return {"status": "ignored"}

        logger.info("Received incoming WhatsApp message", extra={"sender": sender, "text": text_body})
        
        # Get or create user and process message normally (no automatic reset)
        user = get_or_create_user(sender, db=db)
        state_manager = StateManager(db)
        
        # Route message to appropriate flow handler (old GPS repair or new service engineer)
        from app.services.flow_router import route_message
        answer = route_message(user, text_body, state_manager, db)
        
        # Send response and save chat
        send_whatsapp_message(user.phone_number, answer)
        save_chat(user.phone_number, text_body, answer)
        
        logger.info(
            "Message processed successfully",
            extra={"phone_number": user.phone_number, "response_length": len(answer)}
        )
        
    except Exception as exc:
        logger.exception("Unexpected error processing webhook", exc_info=exc)
        if sender:
            try:
                send_whatsapp_message(sender, TECHNICAL_ERROR_MESSAGE)
            except Exception:
                logger.exception("Failed to send technical error message to sender")
        return {"status": "error", "detail": str(exc)}

    return {"status": "ok"}
