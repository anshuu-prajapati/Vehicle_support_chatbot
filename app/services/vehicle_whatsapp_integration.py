"""
Vehicle WhatsApp Integration Service
Integrates vehicle API with WhatsApp conversation flow
"""
import logging
from typing import Optional

from app.services.vehicle_api_service import VehicleAPIService
from app.schemas.vehicle_schema import VehicleDetails, VehicleStatus

logger = logging.getLogger("app.vehicle_whatsapp_integration")


class VehicleWhatsAppIntegration:
    """
    Service to integrate vehicle API with WhatsApp conversation flow
    """

    def __init__(self, vehicle_service: Optional[VehicleAPIService] = None):
        """
        Initialize vehicle WhatsApp integration

        Args:
            vehicle_service: VehicleAPIService instance
        """
        self.vehicle_service = vehicle_service or VehicleAPIService()

    async def close(self):
        """Close service connections"""
        if self.vehicle_service:
            await self.vehicle_service.close()

    def _format_vehicle_status_emoji(self, status: VehicleStatus) -> str:
        """Get emoji for vehicle status"""
        status_emojis = {
            VehicleStatus.ONLINE: "🟢",
            VehicleStatus.OFFLINE: "🔴",
            VehicleStatus.NOT_WORKING: "⚠️",
            VehicleStatus.UNKNOWN: "❓",
        }
        return status_emojis.get(status, "❓")

    def _format_vehicle_status_hindi(self, status: VehicleStatus) -> str:
        """Get Hindi text for vehicle status"""
        status_hindi = {
            VehicleStatus.ONLINE: "Online",
            VehicleStatus.OFFLINE: "Offline",
            VehicleStatus.NOT_WORKING: "Kaam Nahi Kar Raha",
            VehicleStatus.UNKNOWN: "Status Pata Nahi",
        }
        return status_hindi.get(status, "Status Pata Nahi")

    async def validate_and_fetch_vehicle(self, vehicle_number: str) -> tuple[bool, str, Optional[VehicleDetails]]:
        """
        Validate vehicle exists and fetch details

        Args:
            vehicle_number: Vehicle registration number

        Returns:
            Tuple of (is_valid, message, vehicle_details)
            - is_valid: Whether vehicle was found
            - message: WhatsApp message to send
            - vehicle_details: VehicleDetails object if found, None otherwise
        """
        try:
            logger.info(
                "Validating vehicle for WhatsApp flow",
                extra={"vehicle_number": vehicle_number},
            )

            vehicle_details = await self.vehicle_service.get_vehicle_details(vehicle_number)

            if not vehicle_details:
                logger.warning(
                    "Vehicle not found in WhatsApp flow",
                    extra={"vehicle_number": vehicle_number},
                )
                return False, self._format_vehicle_not_found_message(vehicle_number), None

            logger.info(
                "Vehicle found in WhatsApp flow",
                extra={
                    "vehicle_number": vehicle_number,
                    "status": vehicle_details.status,
                },
            )

            message = self._format_vehicle_found_message(vehicle_details)
            return True, message, vehicle_details

        except Exception as e:
            logger.error(
                "Error validating vehicle in WhatsApp flow",
                extra={"vehicle_number": vehicle_number, "error": str(e)},
            )
            return False, self._format_vehicle_error_message(), None

    def _format_vehicle_not_found_message(self, vehicle_number: str) -> str:
        """Format message when vehicle is not found"""
        return (
            f"❌ Vehicle {vehicle_number} nahi mila.\n\n"
            "Kripya vehicle number dobara check karein aur phir se bhejein."
        )

    def _format_vehicle_error_message(self) -> str:
        """Format message when there's an error fetching vehicle"""
        return (
            "⚠️ Vehicle ki jaankari lene mein problem aa rahi hai.\n\n"
            "Kripya thodi der baad dobara try karein."
        )

    def _format_vehicle_found_message(self, vehicle: VehicleDetails) -> str:
        """
        Format WhatsApp message when vehicle is found

        Args:
            vehicle: VehicleDetails object

        Returns:
            Formatted WhatsApp message
        """
        status_emoji = self._format_vehicle_status_emoji(vehicle.status)
        status_text = self._format_vehicle_status_hindi(vehicle.status)

        message_parts = [
            f"✅ Vehicle Mil Gaya!\n",
            f"📋 Vehicle Number: {vehicle.vehicle_number}",
            f"{status_emoji} Status: {status_text}",
        ]

        # Add location if available
        if vehicle.last_location and vehicle.last_location.address:
            message_parts.append(f"📍 Last Location: {vehicle.last_location.address}")

        # Add owner info if available
        if vehicle.owner_name:
            message_parts.append(f"👤 Owner: {vehicle.owner_name}")

        # Add last update time if available
        if vehicle.last_update_time:
            message_parts.append(
                f"🕐 Last Update: {vehicle.last_update_time.strftime('%d-%m-%Y %H:%M')}"
            )

        message_parts.append("")  # Empty line

        # Add action prompt based on status
        if vehicle.status == VehicleStatus.NOT_WORKING:
            message_parts.append("⚠️ Yeh vehicle kaam nahi kar raha hai.")
            message_parts.append("\nKya aap troubleshooting start karna chahenge?")
            message_parts.append("1️⃣ Haan")
            message_parts.append("2️⃣ Nahi")
        elif vehicle.status == VehicleStatus.OFFLINE:
            message_parts.append("🔴 Yeh vehicle offline hai.")
            message_parts.append("\nKya aap troubleshooting start karna chahenge?")
            message_parts.append("1️⃣ Haan")
            message_parts.append("2️⃣ Nahi")
        else:
            message_parts.append("✅ Vehicle online hai aur kaam kar raha hai.")
            message_parts.append("\nKya aapko koi aur madad chahiye?")
            message_parts.append("1️⃣ Haan")
            message_parts.append("2️⃣ Nahi")

        return "\n".join(message_parts)

    def format_vehicle_summary_for_context(self, vehicle: VehicleDetails) -> dict:
        """
        Format vehicle details for conversation context storage

        Args:
            vehicle: VehicleDetails object

        Returns:
            Dictionary with vehicle summary for context
        """
        return {
            "vehicle_number": vehicle.vehicle_number,
            "vehicle_status": vehicle.status.value,
            "vehicle_imei": vehicle.imei,
            "vehicle_owner_name": vehicle.owner_name,
            "vehicle_owner_phone": vehicle.owner_phone,
            "vehicle_driver_name": vehicle.driver_name,
            "vehicle_driver_phone": vehicle.driver_phone,
            "vehicle_last_location": vehicle.last_location.address if vehicle.last_location else None,
            "vehicle_last_update": vehicle.last_update_time.isoformat() if vehicle.last_update_time else None,
        }

    async def get_not_working_vehicles_message(self) -> str:
        """
        Get formatted message with list of not working vehicles

        Returns:
            Formatted WhatsApp message
        """
        try:
            result = await self.vehicle_service.get_not_working_vehicles()

            if result.total_count == 0:
                return "✅ Koi bhi vehicle NOT WORKING status mein nahi hai.\n\nSabhi vehicles theek kaam kar rahe hain!"

            message_parts = [
                f"⚠️ Total {result.total_count} vehicles NOT WORKING hain:\n"
            ]

            for idx, vehicle in enumerate(result.vehicles[:10], 1):  # Limit to 10 vehicles
                owner_info = f" - {vehicle.owner_name}" if vehicle.owner_name else ""
                message_parts.append(f"{idx}. {vehicle.vehicle_number}{owner_info}")

            if result.total_count > 10:
                message_parts.append(f"\n... aur {result.total_count - 10} vehicles")

            message_parts.append("\nKisi vehicle ki details dekhne ke liye vehicle number bhejein.")

            return "\n".join(message_parts)

        except Exception as e:
            logger.error(
                "Error fetching not working vehicles for WhatsApp",
                extra={"error": str(e)},
            )
            return self._format_vehicle_error_message()
