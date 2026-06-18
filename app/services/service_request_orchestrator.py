"""
Service Request Orchestrator

Purpose: Handle customer's first reply after GPS Alert message.
This module works independently and can later replace existing flow logic.

Flow:
GPS Alert Message → Customer Reply → Orchestrator → LLM Understanding →
Extract Information → Determine Case Type → Generate Response

Note: This file is NOT connected to any existing flow yet.
"""

import json
import logging
from typing import Dict, Optional, Tuple, List
from datetime import datetime
from sqlalchemy.orm import Session
import re

from app.ai.groq_llm import generate_response
from app.db.models.conversation_state import ConversationState

logger = logging.getLogger(__name__)


class ServiceRequestOrchestrator:
    """
    Orchestrates the service request process after GPS alert.

    Responsibilities:
    1. Read customer's first reply after GPS Alert
    2. Understand intent using LLM
    3. Extract all available information
    4. Store information in service request JSON
    5. Determine case type (Case Closed or Service Required)
    6. Generate appropriate response
    """

    CASE_CLOSED_TYPES = [
        "workshop",
        "accident",
        "battery_disconnect",
        "gps_removed_maintenance"
    ]

    SERVICE_REQUIRED_TYPES = [
        "gps_damaged",
        "gps_removed_reinstall",
        "vehicle_running_gps_not_updating",
        "vehicle_standing_less_48h",
        "other_gps_issue"
    ]

    INTENT_PRIORITY = {
        "gps_damaged": 100,
        "gps_removed_reinstall": 90,
        "accident": 80,
        "battery_disconnect": 70,
        "workshop": 60,
        "vehicle_running_gps_not_updating": 50,
        "vehicle_standing_less_48h": 40,
        "other_gps_issue": 30,
        "gps_removed_maintenance": 20,
        "unclear": 0
    }

    # FIX #2: expanded acknowledgement list — covers haa, ha, ji, bilkul and
    # common Hinglish variants that were missing before.
    ACKNOWLEDGEMENT_KEYWORDS = [
        "ok", "okay", "theek", "thik",
        "han", "haan", "haa", "ha",
        "yes", "y",
        "ji", "ji haan", "ji han", "ji ha",
        "accha", "acha", "achha",
        "bilkul", "bilkul theek",
        "thanks", "thank you", "thankyou", "thnx", "thx",
        "dhanyavaad", "shukriya",
        "noted", "done", "received",
        "ho gaya", "kar diya", "samajh gaya", "samajh gayi",
        "theek hai", "thik hai",
    ]

    # FIX #1: canonical mapping from LLM extraction keys → service_request keys.
    # The LLM returns "date" and "time"; the service request expects "service_date"
    # and "service_time".  All other keys happen to match 1-to-1.
    EXTRACTION_KEY_MAP = {
        "date": "service_date",
        "time": "service_time",
        # explicit pass-throughs (belt-and-suspenders)
        "issue_type": "issue_type",
        "origin_city": "origin_city",
        "destination_city": "destination_city",
        "service_location": "service_location",
        "phone": "phone",
        "contact_person": "contact_person",
    }

    def __init__(self, db: Session = None):
        self.db = db
        self.service_request = self._init_service_request()
        self.conversation_state_id = None
        self.pending_question = None

    def _init_service_request(self) -> Dict:
        return {
            "issue_type": None,
            "location": None,
            "origin_city": None,
            "destination_city": None,
            "service_location": None,
            "service_date": None,       # REQUIRED
            "service_time": None,
            "phone": None,              # REQUIRED
            "contact_person": None,
            "case_closed": False,
            "service_required": False,
            "ticket_created": False,
            "raw_messages": [],
            "extracted_info": {},
            "all_messages_merged": "",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

    # ------------------------------------------------------------------ #
    #  Public entry point                                                  #
    # ------------------------------------------------------------------ #

    def process_customer_reply(
        self,
        message: str,
        vehicle_number: str,
        user_phone: str,
        conversation_history: list = None
    ) -> Tuple[str, Dict]:
        """
        Process customer's reply after GPS alert.

        Returns:
            Tuple of (response_message, service_request_json)
        """
        logger.info(
            "[ORCHESTRATOR] Processing reply",
            extra={"vehicle": vehicle_number, "phone": user_phone,
                   "message": message[:120]}
        )

        self._load_or_create_state(user_phone, vehicle_number)

        self.service_request["raw_messages"].append({
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })

        self._merge_message_context(message)
        logger.info("[ORCHESTRATOR] Merged context: %s",
                    self.service_request["all_messages_merged"][:200])

        # --- Acknowledgement short-circuit ---
        if self._is_acknowledgement(message):
            logger.info("[ORCHESTRATOR] Acknowledgement detected")
            if self.pending_question:
                self._save_state()
                return self.pending_question, self.service_request
            # no pending question — polite close
            self._save_state()
            return "Shukriya! Koi aur madad chahiye toh batayein.", self.service_request

        # === INTENT LOCKING: Only classify intent on FIRST message ===
        # Once issue_type is set, we ONLY update entities, never re-classify intent
        intent_already_locked = bool(self.service_request.get("issue_type"))
        
        if intent_already_locked:
            logger.info(
                "[ORCHESTRATOR] Intent LOCKED - issue_type already set: %s",
                self.service_request.get("issue_type")
            )
            logger.info(
                "[ORCHESTRATOR] Subsequent message - will ONLY extract entities, NOT re-classify intent"
            )
            # Reuse the existing issue_type for extraction context
            intent_result = {
                "category": self.service_request.get("issue_type"),
                "confidence": 1.0,
                "is_side_question": False,
                "reasoning": "Intent locked from first message"
            }
        else:
            # Step 1: intent (ONLY on first message)
            logger.info("[ORCHESTRATOR] First message - classifying intent")
            intent_result = self._understand_intent(
                self.service_request["all_messages_merged"],
                conversation_history
            )
            logger.info("[ORCHESTRATOR] Intent detected: %s", json.dumps(intent_result))

        # Side-question check (only if not locked)
        if not intent_already_locked and intent_result.get("is_side_question"):
            logger.info("[ORCHESTRATOR] Side question detected")
            response = self.handle_side_question(message, self.pending_question)
            self._save_state()
            return response, self.service_request

        # Step 2: extract entities (ALWAYS runs - updates missing fields)
        extracted_info = self._extract_information(
            self.service_request["all_messages_merged"],
            intent_result
        )
        logger.info("[ORCHESTRATOR] Raw extracted_info: %s",
                    json.dumps(extracted_info))

        # Step 3: update (with key remapping fix)
        self._update_service_request(extracted_info)
        logger.info(
            "[ORCHESTRATOR] Service request after update: %s",
            json.dumps({
                k: self.service_request.get(k)
                for k in ("issue_type", "origin_city", "destination_city",
                           "service_location", "service_date", "service_time",
                           "phone", "contact_person")
            })
        )

        # Step 4: case type (only determine on first message, reuse on subsequent)
        if intent_already_locked:
            # Case type was already set - retrieve it
            case_type = self.service_request.get("issue_type")
            logger.info("[ORCHESTRATOR] Case type LOCKED (reusing): %s", case_type)
        else:
            # First message - determine case type
            case_type = self._determine_case_type_with_priority(extracted_info)
            logger.info("[ORCHESTRATOR] Case type determined: %s", case_type)

        # Step 5: missing fields
        missing_fields = self._get_missing_fields(case_type)
        logger.info("[ORCHESTRATOR] Missing fields: %s", missing_fields)

        # Step 6: response
        response = self._generate_response(case_type, missing_fields, extracted_info)
        logger.info("[ORCHESTRATOR] Generated response: %s", response)

        self.pending_question = response if missing_fields else None

        self._save_state()
        return response, self.service_request

    # ------------------------------------------------------------------ #
    #  State persistence                                                   #
    # ------------------------------------------------------------------ #

    def _load_or_create_state(self, user_phone: str, vehicle_number: str):
        if not self.db:
            return
        try:
            state = self.db.query(ConversationState).filter(
                ConversationState.user_phone == user_phone,
                ConversationState.vehicle_number == vehicle_number,
                ConversationState.flow_type == "gps_alert_orchestrator"
            ).order_by(ConversationState.updated_at.desc()).first()

            if state:
                self.conversation_state_id = state.id
                if state.context_data:
                    self.service_request = json.loads(state.context_data)
                    logger.info("[ORCHESTRATOR] Restored state id=%s", state.id)
        except Exception as e:
            logger.error("[ORCHESTRATOR] Error loading state: %s", e)

    def _save_state(self):
        if not self.db:
            return
        try:
            self.service_request["updated_at"] = datetime.utcnow().isoformat()
            if self.conversation_state_id:
                state = self.db.query(ConversationState).filter(
                    ConversationState.id == self.conversation_state_id
                ).first()
                if state:
                    state.context_data = json.dumps(self.service_request)
                    state.updated_at = datetime.utcnow()
                    self.db.commit()
            else:
                state = ConversationState(
                    user_phone=self.service_request.get("phone", "unknown"),
                    vehicle_number="unknown",
                    flow_type="gps_alert_orchestrator",
                    current_state="processing",
                    context_data=json.dumps(self.service_request),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                self.db.add(state)
                self.db.commit()
                self.conversation_state_id = state.id
        except Exception as e:
            logger.error("[ORCHESTRATOR] Error saving state: %s", e)
            if self.db:
                self.db.rollback()

    # ------------------------------------------------------------------ #
    #  Message utilities                                                   #
    # ------------------------------------------------------------------ #

    def _merge_message_context(self, new_message: str):
        if self.service_request["all_messages_merged"]:
            self.service_request["all_messages_merged"] += " " + new_message
        else:
            self.service_request["all_messages_merged"] = new_message

    def _is_acknowledgement(self, message: str) -> bool:
        """
        Returns True if the message is a pure acknowledgement.

        Strategy:
        1. Exact match against the expanded keyword list.
        2. Short message (≤ 12 chars) that contains any keyword.
        """
        msg = message.lower().strip()
        msg = re.sub(r"[!.,?।]", "", msg).strip()

        # Exact match (handles multi-word entries like "ji haan")
        if msg in self.ACKNOWLEDGEMENT_KEYWORDS:
            logger.info("[ORCHESTRATOR] Acknowledgement exact match: %s", msg)
            return True

        # Short-message fuzzy match — avoids false positives on longer messages
        # that happen to contain "ok" mid-sentence ("ok meri gaadi Pune mein hai")
        if len(msg) <= 12:
            for kw in self.ACKNOWLEDGEMENT_KEYWORDS:
                if kw in msg:
                    logger.info("[ORCHESTRATOR] Acknowledgement short-match: %s", kw)
                    return True

        return False

    # ------------------------------------------------------------------ #
    #  LLM: intent                                                         #
    # ------------------------------------------------------------------ #

    def _understand_intent(
        self,
        message: str,
        conversation_history: list = None
    ) -> Dict:
        logger.info("[ORCHESTRATOR] Understanding intent")

        system_prompt = """You are an expert at understanding customer messages about GPS tracking issues.

Analyze the customer's message and classify the situation into one of these categories:

CASE CLOSED (No service needed):
1. workshop - Vehicle is at workshop for repair/service
2. accident - Vehicle met with an accident
3. battery_disconnect - Battery was disconnected intentionally
4. gps_removed_maintenance - GPS removed for maintenance

SERVICE REQUIRED:
5. gps_damaged - GPS device is damaged
6. gps_removed_reinstall - GPS was removed and needs reinstallation
7. vehicle_running_gps_not_updating - Vehicle is running but GPS not updating
8. vehicle_standing_less_48h - Vehicle standing for less than 48 hours
9. other_gps_issue - Other GPS related issues

UNCLEAR:
10. unclear - Cannot determine from message, need more information

Also detect if this is a side question unrelated to the GPS issue (e.g. "tum kaun ho?", "yeh number kya hai?").

Respond ONLY in valid JSON, no markdown, no extra text:
{
    "category": "category_name",
    "confidence": 0.0,
    "is_side_question": false,
    "reasoning": "brief explanation"
}"""

        user_prompt = f"Customer message: {message}"
        if conversation_history:
            user_prompt = f"Previous context: {conversation_history}\n\nCurrent message: {message}"

        try:
            response = generate_response(f"{system_prompt}\n\n{user_prompt}")
            clean = response.strip().lstrip("```json").rstrip("```").strip()
            return json.loads(clean)
        except Exception as e:
            logger.error("[ORCHESTRATOR] Intent error: %s", e)
            return {"category": "unclear", "confidence": 0.0,
                    "is_side_question": False, "reasoning": "error"}

    # ------------------------------------------------------------------ #
    #  LLM: extraction                                                     #
    # ------------------------------------------------------------------ #

    def _extract_information(self, message: str, intent_result: Dict) -> Dict:
        """
        Extract all available entities from the merged message context.

        Key names in the returned dict match EXTRACTION_KEY_MAP so that
        _update_service_request can remap them correctly.
        """
        logger.info("[ORCHESTRATOR] Extracting information")

        system_prompt = """You are an expert at extracting information from customer messages in Hindi, English, and Hinglish.

Extract the following fields if present. Return ONLY valid JSON, no markdown, no extra text.

Fields to extract:
- issue_type: what is the GPS/vehicle problem (string or null)
- origin_city: where the vehicle is coming FROM (string or null)
- destination_city: where the vehicle is going TO (string or null)
- service_location: current location or where service is needed — default to destination_city if vehicle is in transit (string or null)
- date: when service is needed or when vehicle will be available (string or null)
- time: specific time mentioned (string or null)
- phone: 10-digit phone number (string or null)
- contact_person: name or role of person to contact (string or null)

Rules:
- If "Delhi se Pune ja rahi hai" → origin_city=Delhi, destination_city=Pune, service_location=Pune
- If "kal 3 baje" → date=tomorrow, time=3 PM
- If "driver ko 8130995093 par call kar lena" → phone=8130995093, contact_person=driver
- Accept dates in any format: kal, aaj, parso, tomorrow, Monday, 22 June, etc. Store them as-is.
- Extract phone numbers that are 10 digits regardless of surrounding text.
- Never invent information that is not present.

Example:
Input: "GPS kharab hai, gaadi Delhi se Pune ja rahi hai, kal 3 baje available hogi, driver ko 8130995093 par call kar lena"
Output:
{
  "issue_type": "GPS not working",
  "origin_city": "Delhi",
  "destination_city": "Pune",
  "service_location": "Pune",
  "date": "tomorrow",
  "time": "3 PM",
  "phone": "8130995093",
  "contact_person": "driver",
  "confidence": 0.95
}

Respond ONLY with JSON. No markdown fences, no explanation."""

        user_prompt = f"Message: {message}\nIntent: {intent_result.get('category', 'unknown')}"

        try:
            raw = generate_response(f"{system_prompt}\n\n{user_prompt}")
            clean = raw.strip().lstrip("```json").rstrip("```").strip()
            extracted = json.loads(clean)
            logger.info("[ORCHESTRATOR] LLM extracted: %s", json.dumps(extracted))
        except Exception as e:
            logger.error("[ORCHESTRATOR] Extraction error: %s", e)
            extracted = {}

        # Regex fallback for phone number — LLM sometimes misses it
        if not extracted.get("phone"):
            phone_match = re.search(r"\b(\d{10})\b", message)
            if phone_match:
                extracted["phone"] = phone_match.group(1)
                logger.info("[ORCHESTRATOR] Regex phone fallback: %s",
                            extracted["phone"])

        return extracted

    # ------------------------------------------------------------------ #
    #  Service request update — FIX #1 applied here                       #
    # ------------------------------------------------------------------ #

    def _update_service_request(self, extracted_info: Dict):
        """
        Write extracted entities into the service request.

        FIX #1: The LLM returns 'date' and 'time'; the service request stores
        'service_date' and 'service_time'.  EXTRACTION_KEY_MAP translates all
        keys before writing.  Only null/empty fields are populated — existing
        values are never overwritten.
        
        CRITICAL: issue_type is LOCKED after first extraction - never overwritten.
        This prevents intent drift across multi-message conversations.
        """
        for raw_key, value in extracted_info.items():
            if not value or raw_key == "confidence":
                continue

            # Translate to the canonical service_request key name
            sr_key = self.EXTRACTION_KEY_MAP.get(raw_key, raw_key)
            
            # === INTENT LOCKING: Never overwrite issue_type once set ===
            if sr_key == "issue_type" and self.service_request.get("issue_type"):
                logger.info(
                    "[ORCHESTRATOR] INTENT LOCKED - Ignoring new issue_type extraction: %s "
                    "(keeping existing: %s)",
                    value,
                    self.service_request.get("issue_type")
                )
                continue

            # Only write if the target field is currently empty
            if sr_key in self.service_request and not self.service_request[sr_key]:
                self.service_request[sr_key] = value
                logger.info("[ORCHESTRATOR] Set %s = %s", sr_key, value)

        # Convenience alias: populate service_location from destination_city
        # when the vehicle is in transit and service_location wasn't explicit.
        if (not self.service_request.get("service_location")
                and self.service_request.get("destination_city")):
            self.service_request["service_location"] = \
                self.service_request["destination_city"]
            logger.info(
                "[ORCHESTRATOR] service_location inferred from destination_city: %s",
                self.service_request["service_location"]
            )

        self.service_request["extracted_info"] = extracted_info

    # ------------------------------------------------------------------ #
    #  Case type determination                                             #
    # ------------------------------------------------------------------ #

    def _determine_case_type_with_priority(self, extracted_info: Dict) -> str:
        issue_type = (extracted_info.get("issue_type") or "").lower()
        detected = []

        keyword_map = {
            "gps_damaged": ["damaged", "broken", "kharab", "not working",
                            "kaam nahi", "damage", "toota"],
            "gps_removed_reinstall": ["removed", "nikala", "ukhad",
                                      "reinstall", "hataya", "wapas lagao"],
            "accident": ["accident", "crash", "collision", "takkar", "hadsa"],
            "battery_disconnect": ["battery disconnect", "battery remove",
                                   "battery nikala", "battery hataya",
                                   "battery band"],
            "workshop": ["workshop", "garage", "repair shop",
                         "service center", "mechanic"],
            "vehicle_running_gps_not_updating": ["running", "chal rahi",
                                                 "moving", "chalu",
                                                 "chalti hai"],
            "vehicle_standing_less_48h": ["standing", "parked", "khadi",
                                          "ruki", "khadi hai"],
            "gps_removed_maintenance": ["maintenance", "checking",
                                        "service ke liye nikala"],
        }

        for case, keywords in keyword_map.items():
            if any(kw in issue_type for kw in keywords):
                detected.append(case)

        if len(detected) > 1:
            case_type = max(detected,
                            key=lambda t: self.INTENT_PRIORITY.get(t, 0))
        elif len(detected) == 1:
            case_type = detected[0]
        else:
            # Fall back to LLM category from intent result stored in extracted_info
            # (caller passes it through intent_result; we re-derive from issue_type string)
            case_type = "other_gps_issue"

        if case_type in self.CASE_CLOSED_TYPES:
            self.service_request["case_closed"] = True
            self.service_request["service_required"] = False
        else:
            self.service_request["case_closed"] = False
            self.service_request["service_required"] = True

        self.service_request["issue_type"] = case_type
        logger.info("[ORCHESTRATOR] Final case type: %s", case_type)
        return case_type

    # ------------------------------------------------------------------ #
    #  Missing field detection                                             #
    # ------------------------------------------------------------------ #

    def _get_missing_fields(self, case_type: str) -> List[str]:
        """
        Returns missing REQUIRED fields for service-required cases.
        Required: service_location, service_date, phone.
        """
        if case_type in self.CASE_CLOSED_TYPES:
            return []

        missing = []
        has_location = (
            self.service_request.get("service_location")
            or self.service_request.get("destination_city")
            or self.service_request.get("origin_city")
        )
        if not has_location:
            missing.append("location")

        if not self.service_request.get("service_date"):
            missing.append("service_date")

        if not self.service_request.get("phone"):
            missing.append("phone")

        logger.info("[ORCHESTRATOR] Missing fields: %s", missing)
        return missing

    # ------------------------------------------------------------------ #
    #  Response generation — FIX #3: template-first, LLM as fallback      #
    # ------------------------------------------------------------------ #

    def _generate_response(
        self,
        case_type: str,
        missing_fields: List[str],
        extracted_info: Dict
    ) -> str:
        """
        Generate a short, natural response.

        FIX #3: Questions for missing fields now use deterministic templates
        that confirm already-known values rather than re-asking for them.
        LLM is only used when the templates don't apply, preventing the
        "context echo" hallucination (bot reflecting user's date back as a
        question instead of confirming it).
        """
        # Case-closed acknowledgements
        if case_type in self.CASE_CLOSED_TYPES:
            responses = {
                "workshop": "Samajh gaye — workshop mein hai. Dhanyavaad!",
                "accident": "Bahut dukh hua yeh sunkar. Kya koi aur madad chahiye?",
                "battery_disconnect": "Theek hai, battery reconnect hone par GPS update ho jayega.",
                "gps_removed_maintenance": "Samajh gaye. Maintenance ke baad GPS waapas kaam karega."
            }
            return responses.get(case_type, "Dhanyavaad! Aapki baat samajh gayi.")

        # All required fields present → create ticket
        if not missing_fields:
            self.service_request["ticket_created"] = True
            loc = (self.service_request.get("service_location")
                   or self.service_request.get("destination_city")
                   or "")
            date = self.service_request.get("service_date", "")
            logger.info("[ORCHESTRATOR] All fields present — ticket created")
            return "✅ Service request create kar di gayi hai. Engineer jald sampark karega."

        # --- Ask for the first missing field using templates ---
        first_missing = missing_fields[0]

        if first_missing == "location":
            return self._ask_location_question()

        if first_missing == "service_date":
            return self._ask_date_question()

        if first_missing == "phone":
            return self._ask_phone_question()

        return "Kripya vehicle ka location, date aur contact number share karein."

    def _ask_location_question(self) -> str:
        """Template-based location question — no LLM call."""
        origin = self.service_request.get("origin_city")
        dest = self.service_request.get("destination_city")
        if origin and dest:
            return f"{origin} se {dest} ja rahi gaadi — {dest} mein kahan service chahiye?"
        if dest:
            return f"Gaadi {dest} mein hai — exact location ya area batayein?"
        return "Gaadi abhi kahan hai?"

    def _ask_date_question(self) -> str:
        """
        Template-based date question.

        If we already have a date in extracted_info but it failed to persist
        (should not happen after Fix #1, but kept as safety net), we surface
        it as a confirmation rather than a blank ask.
        """
        extracted_date = self.service_request.get("extracted_info", {}).get("date")
        if extracted_date:
            # Confirm the date we already heard
            return f"Kya {extracted_date} ko service karwana hai?"
        return "Vehicle kab available hogi service ke liye?"

    def _ask_phone_question(self) -> str:
        """Template-based phone question — no LLM call."""
        contact = self.service_request.get("contact_person")
        if contact:
            return f"{contact.capitalize()} ka contact number kya hai?"
        return "Driver ya contact person ka phone number bataiye."

    # ------------------------------------------------------------------ #
    #  Side question handler                                               #
    # ------------------------------------------------------------------ #

    def handle_side_question(self, message: str, pending_question: str) -> str:
        system_prompt = """You are a helpful GPS support assistant.
The customer asked a side question while you were collecting service details.

Reply briefly (one sentence), then return to the pending question.
Use Hindi-English mix. Format: [Brief answer]. [Pending question]

Example:
Side: "Tum kaun ho?"
Pending: "Gaadi abhi kahan hai?"
Response: "Main GPS Support Assistant hoon. Gaadi abhi kahan hai?"

Respond with just the combined sentence, nothing else."""

        pending = pending_question or "Kripya apni problem batayein."
        try:
            response = generate_response(
                f"{system_prompt}\n\nSide question: {message}\nPending: {pending}"
            )
            return response.strip()
        except Exception:
            return f"Main GPS Support Assistant hoon. {pending}"

    # ------------------------------------------------------------------ #
    #  Public helpers                                                      #
    # ------------------------------------------------------------------ #

    def get_service_request(self) -> Dict:
        return self.service_request

    def reset(self):
        logger.info("[ORCHESTRATOR] Resetting")
        self.service_request = self._init_service_request()
        self.pending_question = None


# ------------------------------------------------------------------ #
#  Convenience function                                                #
# ------------------------------------------------------------------ #

def process_gps_alert_reply(
    message: str,
    vehicle_number: str,
    user_phone: str,
    conversation_history: list = None,
    db: Session = None
) -> Tuple[str, Dict]:
    """
    Convenience function to process customer reply after GPS alert.
    """
    orchestrator = ServiceRequestOrchestrator(db=db)
    return orchestrator.process_customer_reply(
        message=message,
        vehicle_number=vehicle_number,
        user_phone=user_phone,
        conversation_history=conversation_history
    )