import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.models.vehicle import Vehicle
from app.db.models.vehicle_status import VehicleStatus
from app.schemas.vehicle_schema import VehicleStatusUpdateRequest, VehicleStatusUpdateResponse

logger = logging.getLogger("app.vehicle_status_service")


class VehicleStatusService:
    def __init__(self, db: Session):
        self.db = db

    def update_vehicle_status(self, request: VehicleStatusUpdateRequest) -> VehicleStatusUpdateResponse:
        """
        Update vehicle status fields (latitude, longitude, power_state, ignition_state)
        
        Args:
            request: VehicleStatusUpdateRequest with fields to update
            
        Returns:
            VehicleStatusUpdateResponse with operation results
        """
        try:
            # Find the vehicle by vehicle number
            vehicle = self.db.query(Vehicle).filter(
                Vehicle.vehicle_number == request.vehicle_number
            ).first()
            
            if not vehicle:
                logger.warning(f"Vehicle not found: {request.vehicle_number}")
                return VehicleStatusUpdateResponse(
                    success=False,
                    message=f"Vehicle '{request.vehicle_number}' not found in database",
                    vehicle_number=request.vehicle_number,
                    updated_fields={},
                    timestamp=datetime.utcnow()
                )
            
            # Find or create vehicle status record
            vehicle_status = self.db.query(VehicleStatus).filter(
                VehicleStatus.vehicle_id == vehicle.id
            ).first()
            
            if not vehicle_status:
                logger.info(f"Creating new vehicle status record for vehicle {request.vehicle_number}")
                vehicle_status = VehicleStatus(
                    vehicle_id=vehicle.id,
                    mode="unknown",
                    not_working_hours=0
                )
                self.db.add(vehicle_status)
            
            # Track which fields are being updated
            updated_fields = {}
            
            # Update latitude if provided
            if request.latitude is not None:
                old_value = vehicle_status.latitude
                vehicle_status.latitude = request.latitude
                updated_fields["latitude"] = {
                    "old_value": old_value,
                    "new_value": request.latitude
                }
                logger.info(f"Updated latitude for {request.vehicle_number}: {old_value} → {request.latitude}")
            
            # Update longitude if provided
            if request.longitude is not None:
                old_value = vehicle_status.longitude
                vehicle_status.longitude = request.longitude
                updated_fields["longitude"] = {
                    "old_value": old_value,
                    "new_value": request.longitude
                }
                logger.info(f"Updated longitude for {request.vehicle_number}: {old_value} → {request.longitude}")
            
            # Update power_state if provided
            if request.power_state is not None:
                old_value = vehicle_status.power_state
                vehicle_status.power_state = request.power_state
                updated_fields["power_state"] = {
                    "old_value": old_value,
                    "new_value": request.power_state
                }
                logger.info(f"Updated power_state for {request.vehicle_number}: {old_value} → {request.power_state}")
            
            # Update ignition_state if provided
            if request.ignition_state is not None:
                old_value = vehicle_status.ign_state
                vehicle_status.ign_state = request.ignition_state
                updated_fields["ignition_state"] = {
                    "old_value": old_value,
                    "new_value": request.ignition_state
                }
                logger.info(f"Updated ignition_state for {request.vehicle_number}: {old_value} → {request.ignition_state}")
            
            # Update GPS timestamp if location data was provided
            if request.latitude is not None or request.longitude is not None:
                old_gps_time = vehicle_status.last_gps_time
                vehicle_status.last_gps_time = datetime.utcnow()
                updated_fields["last_gps_time"] = {
                    "old_value": old_gps_time.isoformat() if old_gps_time else None,
                    "new_value": vehicle_status.last_gps_time.isoformat()
                }
                logger.info(f"Updated GPS timestamp for {request.vehicle_number}")
            
            # Update location text if coordinates were provided
            if request.latitude is not None and request.longitude is not None:
                old_location = vehicle_status.location
                vehicle_status.location = f"GPS: {request.latitude}, {request.longitude}"
                updated_fields["location"] = {
                    "old_value": old_location,
                    "new_value": vehicle_status.location
                }
                logger.info(f"Updated location text for {request.vehicle_number}")
            
            # Check if any fields were actually updated
            if not updated_fields:
                return VehicleStatusUpdateResponse(
                    success=False,
                    message="No fields provided for update",
                    vehicle_number=request.vehicle_number,
                    updated_fields={},
                    timestamp=datetime.utcnow()
                )
            
            # Commit the changes
            self.db.commit()
            self.db.refresh(vehicle_status)
            
            logger.info(
                f"Successfully updated vehicle status for {request.vehicle_number}",
                extra={
                    "vehicle_number": request.vehicle_number,
                    "updated_fields": list(updated_fields.keys()),
                    "vehicle_id": vehicle.id
                }
            )
            
            return VehicleStatusUpdateResponse(
                success=True,
                message=f"Successfully updated {len(updated_fields)} field(s) for vehicle {request.vehicle_number}",
                vehicle_number=request.vehicle_number,
                updated_fields=updated_fields,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            self.db.rollback()
            logger.error(
                f"Error updating vehicle status for {request.vehicle_number}: {str(e)}",
                extra={"vehicle_number": request.vehicle_number},
                exc_info=True
            )
            return VehicleStatusUpdateResponse(
                success=False,
                message=f"Database error: {str(e)}",
                vehicle_number=request.vehicle_number,
                updated_fields={},
                timestamp=datetime.utcnow()
            )

    def get_vehicle_status(self, vehicle_number: str) -> Optional[Dict[str, Any]]:
        """
        Get current vehicle status information
        
        Args:
            vehicle_number: Vehicle registration number
            
        Returns:
            Dictionary with current status or None if not found
        """
        try:
            # Normalize vehicle number
            vehicle_number = vehicle_number.strip().upper().replace(" ", "")
            
            # Find the vehicle and its status
            result = self.db.query(Vehicle, VehicleStatus).join(
                VehicleStatus, Vehicle.id == VehicleStatus.vehicle_id, isouter=True
            ).filter(Vehicle.vehicle_number == vehicle_number).first()
            
            if not result:
                logger.warning(f"Vehicle not found: {vehicle_number}")
                return None
                
            vehicle, status = result
            
            return {
                "vehicle_number": vehicle.vehicle_number,
                "company_name": vehicle.company_name,
                "latitude": status.latitude if status else None,
                "longitude": status.longitude if status else None,
                "power_state": status.power_state if status else None,
                "ignition_state": status.ign_state if status else None,
                "mode": status.mode if status else None,
                "location": status.location if status else None,
                "last_gps_time": status.last_gps_time.isoformat() if status and status.last_gps_time else None,
                "not_working_hours": status.not_working_hours if status else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting vehicle status for {vehicle_number}: {str(e)}", exc_info=True)
            return None