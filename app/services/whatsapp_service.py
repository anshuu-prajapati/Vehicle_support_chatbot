# app/services/whatsapp_service.py

import logging
import requests

from app.core.config import (
    ACCESS_TOKEN,
    PHONE_NUMBER_ID,
)

logger = logging.getLogger("app.whatsapp_service")

def send_whatsapp_message(to: str, message: str):
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }

    response = requests.post(url, headers=headers, json=payload)
    try:
        response_data = response.json()
    except ValueError:
        response_data = {"error": "invalid_json_response"}

    logger.info(
        "WhatsApp send message response",
        extra={"to": to, "status_code": response.status_code, "response": response_data},
    )

    if response.status_code != 200:
        logger.error(
            "WhatsApp API returned non-200 status",
            extra={"to": to, "status_code": response.status_code, "response": response_data},
        )
        response.raise_for_status()

    return response_data
