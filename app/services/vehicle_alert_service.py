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
        Get all vehicles with GPS issues and their contact information
        
        Finds broken vehicles on-the-fly by checking vehicle_statuses table.
        No alerts table required - just parse data when API is called.
        
        Returns:
            List of vehicles with GPS issues and contact details
        """
        try:
            # Query for vehicles with GPS issues (not working mode)
            # Simplified query - no alerts table required!
            broken_vehicles = (
                self.db.query(Vehicle, VehicleStatus, User)
                .join(VehicleStatus, Vehicle.id == VehicleStatus.vehicle_id)
                .outerjoin(User, Vehicle.manager_id == User.id)
                .filter(VehicleStatus.mode == "not working")
                .all()
            )

            logger.info(f"Found {len(broken_vehicles)} broken vehicles with mode='not working'")

            vehicles_data = []
            for vehicle, status, manager in broken_vehicles:
                # Get vehicle contacts
                contacts = (
                    self.db.query(VehicleContact)
                    .filter(VehicleContact.vehicle_number == vehicle.vehicle_number)
                    .all()
                )

                vehicle_info = {
                    "vehicle_id": vehicle.id,
                    "vehicle_number": vehicle.vehicle_number,
                    "company_name": vehicle.company_name or "Tech Solutions Pvt Ltd",
                    "location": status.location or "Unknown location",
                    "last_gps_time": status.last_gps_time.strftime("%Y-%m-%d %H:%M:%S") if status.last_gps_time else None,
                    "not_working_hours": status.not_working_hours if hasattr(status, 'not_working_hours') else None,
                    "ign_state": status.ign_state,
                    "power_state": status.power_state,
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

            logger.info(f"Prepared {len(vehicles_data)} vehicles data for alerts")
            return vehicles_data

        except Exception as e:
            logger.exception("Error getting broken vehicles with contacts", exc_info=e)
            raise

    def send_alert_to_managers(self, vehicles_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send WhatsApp alerts to managers about vehicles with GPS issues
        
        Args:
            vehicles_data: List of vehicles with GPS issues data
            
        Returns:
            Dict with send results
        """
        if not vehicles_data:
            return {
                "success": True,
                "message": "No vehicles with GPS issues found",
                "alerts_sent": 0,
                "failed_sends": []
            }

        # Create alert message - NEW FORMAT
        vehicle_count = len(vehicles_data)
        
        # Build message for each vehicle
        messages_to_send = {}
        
        for vehicle in vehicles_data:
            vehicle_number = vehicle['vehicle_number']
            location = vehicle['location'] or "Unknown"
            last_gps = vehicle['last_gps_time'] or "Unknown"
            
            # Create personalized message for this vehicle
            msg = f"Namaste Sir,\n\n"
            msg += f"Vehicle *{vehicle_number}* se GPS data receive nahi ho raha hai.\n\n"
            msg += f"📍 Last Known Location: {location}\n"
            msg += f"🕐 Last Update: {last_gps}\n\n"
            msg += "Kripya issue ka reason select karein:\n\n"
            msg += "1️⃣ Workshop / Service Center\n"
            msg += "2️⃣ Accident\n"
            msg += "3️⃣ Battery Disconnect\n"
            msg += "4️⃣ GPS Removed\n"
            msg += "5️⃣ GPS Damaged\n"
            msg += "6️⃣ Vehicle Running but GPS Not Updating\n"
            msg += "7️⃣ Vehicle Standing\n"
            msg += "8️⃣ Other\n\n"
            msg += "Reply with the option number."
            
            # Store message with vehicle context
            for contact in vehicle['contacts']:
                if contact['owner_phone']:
                    if contact['owner_phone'] not in messages_to_send:
                        messages_to_send[contact['owner_phone']] = {
                            'message': msg,
                            'vehicle_number': vehicle_number,
                            'location': location,
                            'last_gps': last_gps
                        }
            
            # Also send to manager
            if vehicle['manager_phone']:
                if vehicle['manager_phone'] not in messages_to_send:
                    messages_to_send[vehicle['manager_phone']] = {
                        'message': msg,
                        'vehicle_number': vehicle_number,
                        'location': location,
                        'last_gps': last_gps
                    }
        
        # For backward compatibility, create a summary message variable
        message = f"Namaste Sir,\n\nVehicle GPS data receive nahi ho raha hai.\n\n"
        message += "Kripya issue ka reason select karein:\n"
        message += "1️⃣ Workshop / Service Center\n"
        message += "2️⃣ Accident\n"
        message += "3️⃣ Battery Disconnect\n"
        message += "4️⃣ GPS Removed\n"
        message += "5️⃣ GPS Damaged\n"
        message += "6️⃣ Vehicle Running but GPS Not Updating\n"
        message += "7️⃣ Vehicle Standing\n"
        message += "8️⃣ Other\n\n"
        message += "Reply with the option number."

        # Send personalized messages to each contact
        sent_count = 0
        failed_sends = []

        for phone, msg_data in messages_to_send.items():
            try:
                logger.info(f"Sending vehicle alert to {phone} for vehicle {msg_data['vehicle_number']}")
                send_whatsapp_message(phone, msg_data['message'])
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
            "message": f"GPS alert sent to {sent_count} manager(s) about {vehicle_count} vehicle(s) with GPS issues",
            "vehicles_count": vehicle_count,
            "alerts_sent": sent_count,
            "failed_sends": failed_sends,
            "vehicles_data": vehicles_data
        }