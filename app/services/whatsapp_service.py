# app/services/whatsapp_service.py

import logging
import requests

from app.core.config import (
    ACCESS_TOKEN,
    PHONE_NUMBER_ID
)

logger = logging.getLogger(__name__)

def send_whatsapp_message(to: str, message: str) -> bool:
    """Send a WhatsApp message via Meta Graph API.
    
    Args:
        to: Recipient phone number
        message: Message text to send
        
    Returns:
        True if message sent successfully, False otherwise
        
    Raises:
        ValueError: If required environment variables are missing
    """
    
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        logger.error("Missing WhatsApp credentials: ACCESS_TOKEN=%s, PHONE_NUMBER_ID=%s", 
                    bool(ACCESS_TOKEN), bool(PHONE_NUMBER_ID))
        raise ValueError("WhatsApp credentials not configured")

    url = (
        f"https://graph.facebook.com/v25.0/"
        f"{PHONE_NUMBER_ID}/messages"
    )

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {
            "body": message
        }
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=10
        )

        logger.debug("WhatsApp API response status: %d", response.status_code)
        
        if response.status_code == 200:
            response_data = response.json()
            logger.info("WhatsApp message sent successfully to %s: %s", to, response_data)
            return True
        else:
            error_data = response.json()
            logger.error("WhatsApp API error (status %d): %s", response.status_code, error_data)
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error("Failed to send WhatsApp message to %s: %s", to, str(e))
        return False
    except Exception as e:
        logger.error("Unexpected error sending WhatsApp message to %s: %s", to, str(e))
        return False