# app/services/whatsapp_service.py

import logging
import requests
import json

from app.core.config import (
    ACCESS_TOKEN,
    PHONE_NUMBER_ID,
)

logger = logging.getLogger("app.whatsapp_service")

def send_whatsapp_message(to: str, message: str):
    """
    Send WhatsApp message with comprehensive logging and error handling.
    
    Args:
        to: Phone number in E.164 format (e.g., +919876543210)
        message: Message content to send
    
    Returns:
        dict: WhatsApp API response
        
    Raises:
        requests.HTTPError: For HTTP errors
        ValueError: For API errors
    """
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

    # Log the request details
    logger.info(
        "Sending WhatsApp message request",
        extra={
            "to": to,
            "message_length": len(message),
            "url": url,
            "phone_number_id": PHONE_NUMBER_ID,
            "payload": payload
        }
    )

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        # Log raw response
        logger.info(
            "WhatsApp API raw response",
            extra={
                "to": to,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "raw_content": response.text[:1000]  # Log first 1000 chars
            }
        )
        
        # Try to parse JSON response
        try:
            response_data = response.json()
        except ValueError as json_error:
            logger.error(
                "WhatsApp API returned invalid JSON",
                extra={
                    "to": to,
                    "status_code": response.status_code,
                    "raw_content": response.text,
                    "json_error": str(json_error)
                }
            )
            response_data = {
                "error": "invalid_json_response",
                "raw_content": response.text,
                "json_error": str(json_error)
            }

        # Enhanced response logging
        logger.info(
            "WhatsApp API parsed response",
            extra={
                "to": to,
                "status_code": response.status_code,
                "response_data": response_data
            }
        )

        # Handle different types of errors
        if response.status_code != 200:
            error_details = {
                "status_code": response.status_code,
                "response": response_data,
                "to": to
            }
            
            # Extract specific error information
            if isinstance(response_data, dict) and "error" in response_data:
                error_info = response_data["error"]
                error_details.update({
                    "error_code": error_info.get("code"),
                    "error_type": error_info.get("type"),
                    "error_message": error_info.get("message"),
                    "error_subcode": error_info.get("error_subcode")
                })
            
            logger.error(
                "WhatsApp API returned error status",
                extra=error_details
            )
            
            # Create meaningful error message based on error type
            if response.status_code == 400:
                if isinstance(response_data, dict) and "error" in response_data:
                    error_msg = response_data["error"].get("message", "Bad request")
                    if "phone number" in error_msg.lower():
                        raise ValueError(f"Invalid phone number format: {error_msg}")
                    elif "message" in error_msg.lower():
                        raise ValueError(f"Message format error: {error_msg}")
                    else:
                        raise ValueError(f"WhatsApp API error: {error_msg}")
                raise ValueError(f"Bad request to WhatsApp API: {response_data}")
            elif response.status_code == 401:
                raise ValueError("WhatsApp API authentication failed - check access token")
            elif response.status_code == 403:
                raise ValueError("WhatsApp API access forbidden - check permissions")
            elif response.status_code == 429:
                raise ValueError("WhatsApp API rate limit exceeded - please try again later")
            elif response.status_code >= 500:
                raise ValueError("WhatsApp API server error - please try again")
            else:
                response.raise_for_status()

        # Success case logging
        message_id = None
        if isinstance(response_data, dict) and "messages" in response_data:
            messages = response_data["messages"]
            if messages and len(messages) > 0:
                message_id = messages[0].get("id")
        
        logger.info(
            "WhatsApp message sent successfully",
            extra={
                "to": to,
                "message_id": message_id,
                "response": response_data
            }
        )

        return response_data

    except requests.exceptions.Timeout:
        logger.error(
            "WhatsApp API request timed out",
            extra={"to": to, "timeout": 30}
        )
        raise ValueError("WhatsApp API request timed out - please try again")
    
    except requests.exceptions.ConnectionError as e:
        logger.error(
            "WhatsApp API connection error",
            extra={"to": to, "connection_error": str(e)}
        )
        raise ValueError("Unable to connect to WhatsApp API - please check internet connection")
    
    except requests.exceptions.RequestException as e:
        logger.error(
            "WhatsApp API request failed",
            extra={"to": to, "request_error": str(e)}
        )
        raise ValueError(f"WhatsApp API request failed: {str(e)}")
