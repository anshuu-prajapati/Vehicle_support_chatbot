import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from datetime import datetime

from app.db.models.vehicle import Vehicle
from app.db.models.vehicle_status import VehicleStatus
from app.db.models.alert import Alert
from app.db.models.user import User
from app.db.models.vehicle_contact import VehicleContact
from app.services.whatsapp_service import send_whatsapp_message

logger = logging.getLogger("app.vehicle_alert_service")


class VehicleAlertService:
    def __init__(self, db: Session):
        self.db = db

    def get_broken_vehicles_with_contacts(self) -> List[Dict[str, Any]]:
        """
        Get all broken/not-working vehicles with their contact information
        
        Returns:
            List of broken vehicles with contact details
        """
        try:
            # Query for vehicles that are not working
            broken_vehicles = (
                self.db.query(Vehicle, VehicleStatus, Alert, User)
                .join(VehicleStatus, Vehicle.id == VehicleStatus.vehicle_id)
                .join(Alert, Vehicle.id == Alert.vehicle_id)
                .outerjoin(User, Vehicle.manager_id == User.id)
                .filter(VehicleStatus.mode == "not working")
                .filter(Alert.status == "OPEN")
                .filter(Alert.alert_type == "VEHICLE_OFF_NOT_WORKING")
                .all()
            )

            vehicles_data = []
            for vehicle, status, alert, manager in broken_vehicles:
                # Get vehicle contacts
                contacts = (
                    self.db.query(VehicleContact)
                    .filter(VehicleContact.vehicle_number == vehicle.vehicle_number)
                    .all()
                )

                vehicle_info = {
                    "vehicle_id": vehicle.id,
                    "vehicle_number": vehicle.vehicle_number,
                    "location": status.location or "Unknown location",
                    "last_gps_time": status.last_gps_time.strftime("%Y-%m-%d %H:%M:%S") if status.last_gps_time else None,
                    "alert_created": alert.created_at.strftime("%Y-%m-%d %H:%M:%S") if alert.created_at else None,
                    "manager_name": manager.name if manager else "No manager assigned",
                    "manager_phone": manager.phone_number if manager else None,
                    "contacts": []
                }

                # Add vehicle contacts
                for contact in contacts:
                    contact_info = {
                        "type": contact.contact_type,
                        "owner_phone": contact.owner_phone,
                        "driver_phone": contact.driver_phone,
                        "is_primary": contact.is_primary
                    }
                    vehicle_info["contacts"].append(contact_info)

                vehicles_data.append(vehicle_info)

            return vehicles_data

        except Exception as e:
            logger.exception("Error getting broken vehicles with contacts", exc_info=e)
            raise

    def send_alert_to_managers(self, vehicles_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send WhatsApp alerts to managers about broken vehicles
        
        Args:
            vehicles_data: List of broken vehicles data
            
        Returns:
            Dict with send results
        """
        if not vehicles_data:
            return {
                "success": True,
                "message": "No broken vehicles found",
                "alerts_sent": 0,
                "failed_sends": []
            }

        # Create alert message
        vehicle_count = len(vehicles_data)
        message = f"🚨 *VEHICLE ALERT* 🚨\n\n"
        message += f"Aapke fleet mein *{vehicle_count}* vehicle(s) breakdown/not working hai:\n\n"

        for i, vehicle in enumerate(vehicles_data, 1):
            message += f"*{i}. Vehicle {vehicle['vehicle_number']}*\n"
            message += f"📍 Location: {vehicle['location']}\n"
            
            if vehicle['last_gps_time']:
                message += f"🕐 Last GPS: {vehicle['last_gps_time']}\n"
            
            if vehicle['alert_created']:
                message += f"⏰ Alert Time: {vehicle['alert_created']}\n"
            
            # Add contact info
            for contact in vehicle['contacts']:
                if contact['type'] == 'OWNER' and contact['owner_phone']:
                    message += f"👤 Owner: {contact['owner_phone']}\n"
                if contact['type'] == 'DRIVER' and contact['driver_phone']:
                    message += f"🚛 Driver: {contact['driver_phone']}\n"
            
            message += "\n"

        message += "Do you need assistance? Reply with:\n"
        message += "1️⃣ YES - Engineer assistance chahiye\n"
        message += "2️⃣ NO - We are handling it\n\n"
        message += "Support Team"

        # Send to all unique manager phones
        manager_phones = set()
        for vehicle in vehicles_data:
            if vehicle['manager_phone']:
                manager_phones.add(vehicle['manager_phone'])
            # Also add owner phones as managers
            for contact in vehicle['contacts']:
                if contact['owner_phone']:
                    manager_phones.add(contact['owner_phone'])

        sent_count = 0
        failed_sends = []

        for phone in manager_phones:
            try:
                logger.info(f"Sending vehicle alert to {phone}")
                send_whatsapp_message(phone, message)
                sent_count += 1
                logger.info(f"Successfully sent alert to {phone}")
            except Exception as e:
                logger.error(f"Failed to send alert to {phone}: {str(e)}")
                failed_sends.append({
                    "phone": phone,
                    "error": str(e)
                })

        return {
            "success": sent_count > 0,
            "message": f"Alert sent to {sent_count} manager(s) about {vehicle_count} broken vehicle(s)",
            "vehicles_count": vehicle_count,
            "alerts_sent": sent_count,
            "failed_sends": failed_sends,
            "vehicles_data": vehicles_data
        }