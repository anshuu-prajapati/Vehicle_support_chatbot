from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from app.db.database import SessionLocal
from app.db.models.vehicle import Vehicle
from app.db.models.vehicle_status import VehicleStatus
from app.db.models.user import User
from app.schemas.vehicle_schema import (
    VehicleCreate,
    VehicleUpdate,
    VehicleStatusCreate,
    VehicleResponse,
    VehicleDetailResponse
)

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


@router.post("/", response_model=VehicleResponse)
def create_vehicle(vehicle_data: VehicleCreate):
    """Create a new vehicle with optional manager, supervisor, and driver assignments"""
    db = SessionLocal()
    try:
        # Check if vehicle already exists
        existing = db.query(Vehicle).filter(
            Vehicle.vehicle_number == vehicle_data.vehicle_number
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Vehicle with this number already exists")
        
        # Validate that assigned users exist
        if vehicle_data.manager_id:
            manager = db.query(User).filter(User.id == vehicle_data.manager_id).first()
            if not manager:
                raise HTTPException(status_code=404, detail="Manager not found")
        
        if vehicle_data.supervisor_id:
            supervisor = db.query(User).filter(User.id == vehicle_data.supervisor_id).first()
            if not supervisor:
                raise HTTPException(status_code=404, detail="Supervisor not found")
        
        if vehicle_data.driver_id:
            driver = db.query(User).filter(User.id == vehicle_data.driver_id).first()
            if not driver:
                raise HTTPException(status_code=404, detail="Driver not found")
        
        # Create new vehicle
        new_vehicle = Vehicle(
            vehicle_number=vehicle_data.vehicle_number,
            manager_id=vehicle_data.manager_id,
            supervisor_id=vehicle_data.supervisor_id,
            driver_id=vehicle_data.driver_id
        )
        
        db.add(new_vehicle)
        db.commit()
        db.refresh(new_vehicle)
        
        return new_vehicle
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/", response_model=List[VehicleResponse])
def get_all_vehicles(skip: int = 0, limit: int = 100):
    """Get all vehicles"""
    db = SessionLocal()
    try:
        vehicles = db.query(Vehicle).offset(skip).limit(limit).all()
        return vehicles
    finally:
        db.close()


@router.get("/{vehicle_id}", response_model=VehicleDetailResponse)
def get_vehicle(vehicle_id: int):
    """Get a specific vehicle by ID with all details"""
    db = SessionLocal()
    try:
        vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        
        return vehicle
    finally:
        db.close()


@router.get("/number/{vehicle_number}", response_model=VehicleDetailResponse)
def get_vehicle_by_number(vehicle_number: str):
    """Get a specific vehicle by vehicle number"""
    db = SessionLocal()
    try:
        vehicle = db.query(Vehicle).filter(
            Vehicle.vehicle_number == vehicle_number
        ).first()
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        
        return vehicle
    finally:
        db.close()


@router.put("/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle(vehicle_id: int, vehicle_data: VehicleUpdate):
    """Update a vehicle"""
    db = SessionLocal()
    try:
        vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        
        # Update fields if provided
        if vehicle_data.vehicle_number is not None:
            # Check if new vehicle number already exists
            existing = db.query(Vehicle).filter(
                Vehicle.vehicle_number == vehicle_data.vehicle_number,
                Vehicle.id != vehicle_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="Vehicle number already exists")
            vehicle.vehicle_number = vehicle_data.vehicle_number
        
        if vehicle_data.manager_id is not None:
            if vehicle_data.manager_id != 0:  # 0 means unassign
                manager = db.query(User).filter(User.id == vehicle_data.manager_id).first()
                if not manager:
                    raise HTTPException(status_code=404, detail="Manager not found")
            vehicle.manager_id = vehicle_data.manager_id if vehicle_data.manager_id != 0 else None
        
        if vehicle_data.supervisor_id is not None:
            if vehicle_data.supervisor_id != 0:
                supervisor = db.query(User).filter(User.id == vehicle_data.supervisor_id).first()
                if not supervisor:
                    raise HTTPException(status_code=404, detail="Supervisor not found")
            vehicle.supervisor_id = vehicle_data.supervisor_id if vehicle_data.supervisor_id != 0 else None
        
        if vehicle_data.driver_id is not None:
            if vehicle_data.driver_id != 0:
                driver = db.query(User).filter(User.id == vehicle_data.driver_id).first()
                if not driver:
                    raise HTTPException(status_code=404, detail="Driver not found")
            vehicle.driver_id = vehicle_data.driver_id if vehicle_data.driver_id != 0 else None
        
        db.commit()
        db.refresh(vehicle)
        
        return vehicle
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.delete("/{vehicle_id}")
def delete_vehicle(vehicle_id: int):
    """Delete a vehicle"""
    db = SessionLocal()
    try:
        vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        
        db.delete(vehicle)
        db.commit()
        
        return {
            "status": "success",
            "message": f"Vehicle {vehicle_id} deleted successfully",
            "vehicle_id": vehicle_id,
            "vehicle_number": vehicle.vehicle_number
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/{vehicle_id}/status", response_model=dict)
def create_or_update_vehicle_status(vehicle_id: int, status_data: VehicleStatusCreate):
    """Create or update vehicle status"""
    db = SessionLocal()
    try:
        vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        
        # Check if status exists
        vehicle_status = db.query(VehicleStatus).filter(
            VehicleStatus.vehicle_id == vehicle_id
        ).first()
        
        if vehicle_status:
            # Update existing status
            vehicle_status.ign_state = status_data.ign_state or vehicle_status.ign_state
            vehicle_status.mode = status_data.mode or vehicle_status.mode
            vehicle_status.location = status_data.location or vehicle_status.location
            if status_data.last_gps_time:
                vehicle_status.last_gps_time = datetime.fromisoformat(status_data.last_gps_time)
            vehicle_status.not_working_hours = status_data.not_working_hours
        else:
            # Create new status
            vehicle_status = VehicleStatus(
                vehicle_id=vehicle_id,
                ign_state=status_data.ign_state,
                mode=status_data.mode,
                location=status_data.location,
                last_gps_time=datetime.fromisoformat(status_data.last_gps_time) if status_data.last_gps_time else None,
                not_working_hours=status_data.not_working_hours
            )
            db.add(vehicle_status)
        
        db.commit()
        db.refresh(vehicle_status)
        
        return {
            "status": "success",
            "message": "Vehicle status updated",
            "vehicle_id": vehicle_id,
            "ign_state": vehicle_status.ign_state,
            "mode": vehicle_status.mode,
            "location": vehicle_status.location,
            "not_working_hours": vehicle_status.not_working_hours
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/{vehicle_id}/status", response_model=dict)
def get_vehicle_status(vehicle_id: int):
    """Get vehicle status"""
    db = SessionLocal()
    try:
        vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        
        status = db.query(VehicleStatus).filter(
            VehicleStatus.vehicle_id == vehicle_id
        ).first()
        
        if not status:
            raise HTTPException(status_code=404, detail="Vehicle status not found")
        
        return {
            "vehicle_id": vehicle_id,
            "vehicle_number": vehicle.vehicle_number,
            "ign_state": status.ign_state,
            "mode": status.mode,
            "location": status.location,
            "last_gps_time": status.last_gps_time.isoformat() if status.last_gps_time else None,
            "not_working_hours": status.not_working_hours
        }
    finally:
        db.close()


@router.get("/status/not-working/list", response_model=List[dict])
def get_not_working_vehicles(skip: int = 0, limit: int = 100):
    """Get all vehicles that are NOT WORKING"""
    db = SessionLocal()
    try:
        statuses = db.query(VehicleStatus).filter(
            VehicleStatus.mode == "not working"
        ).offset(skip).limit(limit).all()
        
        result = []
        for status in statuses:
            vehicle = db.query(Vehicle).filter(Vehicle.id == status.vehicle_id).first()
            result.append({
                "vehicle_id": vehicle.id,
                "vehicle_number": vehicle.vehicle_number,
                "ign_state": status.ign_state,
                "mode": status.mode,
                "location": status.location,
                "last_gps_time": status.last_gps_time.isoformat() if status.last_gps_time else None,
                "not_working_hours": status.not_working_hours
            })
        
        return result
    finally:
        db.close()
