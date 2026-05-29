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



















from fastapi import APIRouter, Request

from app.core.config import VERIFY_TOKEN
from app.services.ai_response_service import generate_ai_answer
from app.services.chat_service import save_chat
from app.services.whatsapp_service import send_whatsapp_message

router = APIRouter(
    prefix="/webhook",
    tags=["WhatsApp"]
)


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
async def receive_message(request: Request):
    body = await request.json()
    print(body)

    try:
        entry = body.get("entry")
        if not entry or not isinstance(entry, list):
            return {"status": "ignored"}

        changes = entry[0].get("changes") if entry[0] else None
        if not changes or not isinstance(changes, list):
            return {"status": "ignored"}

        value = changes[0].get("value")
        if not value or "messages" not in value:
            return {"status": "ignored"}

        message = value["messages"][0]
        sender = message.get("from")
        text_body = message.get("text", {}).get("body")

        if not sender or not text_body:
            return {"status": "ignored"}

        print("Sender:", sender)
        print("Message:", text_body)

        answer = generate_ai_answer(text_body)
        send_whatsapp_message(sender, answer)
        save_chat(sender, text_body, answer)
    except Exception as e:
        print("ERROR:", e)
        return {"status": "error", "detail": str(e)}

    return {"status": "ok"}
