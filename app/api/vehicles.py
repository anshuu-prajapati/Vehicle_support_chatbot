"""
Vehicle API Routes
FastAPI endpoints for vehicle monitoring and tracking
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.services.vehicle_alert_service import VehicleAlertService
from app.clients.vehicle_api_client import (
    VehicleAPIClient,
    VehicleAPIException,
    VehicleAPIConnectionError,
    VehicleAPITimeoutError,
    VehicleAPIAuthenticationError,
)
from app.services.vehicle_api_service import VehicleAPIService
from app.schemas.vehicle_schema import (
    VehicleDetails,
    VehicleStatusResponse,
    VehicleLocationResponse,
    VehicleSearchResponse,
    NotWorkingVehiclesResponse,
    VehicleAPIHealthResponse,
    VehicleAlertResponse,
)

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])
logger = logging.getLogger("app.api.vehicles")


# Dependency for vehicle service
async def get_vehicle_service() -> VehicleAPIService:
    """Dependency to get vehicle API service instance"""
    service = VehicleAPIService()
    try:
        yield service
    finally:
        await service.close()


@router.post("/send-breakdown-alerts", response_model=VehicleAlertResponse)
async def send_breakdown_alerts(db: Session = Depends(get_db)):
    """
    Send WhatsApp alerts to managers about broken/not working vehicles
    
    This endpoint:
    1. Queries database for vehicles with 'not working' status
    2. Gets their locations and contact information  
    3. Sends WhatsApp alerts to managers/owners
    4. Returns summary of alerts sent
    
    Returns:
        VehicleAlertResponse with alert sending results and vehicle details
    """
    try:
        logger.info("Processing vehicle breakdown alert request")
        
        # Initialize alert service
        alert_service = VehicleAlertService(db)
        
        # Get broken vehicles data
        broken_vehicles = alert_service.get_broken_vehicles_with_contacts()
        
        if not broken_vehicles:
            return VehicleAlertResponse(
                success=True,
                message="No broken vehicles found at this time",
                vehicles_count=0,
                alerts_sent=0,
                vehicles_data=[]
            )
        
        # Send alerts to managers
        result = alert_service.send_alert_to_managers(broken_vehicles)
        
        logger.info(
            f"Vehicle alert process completed: {result['alerts_sent']} alerts sent for {result['vehicles_count']} vehicles"
        )
        
        return VehicleAlertResponse(**result)
        
    except Exception as e:
        logger.exception("Error processing vehicle breakdown alerts", exc_info=e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process vehicle alerts: {str(e)}"
        )


@router.get("/breakdown-status", response_model=VehicleAlertResponse) 
async def get_breakdown_status(db: Session = Depends(get_db)):
    """
    Get current status of broken/not working vehicles without sending alerts
    
    Returns:
        VehicleAlertResponse with current broken vehicles information
    """
    try:
        logger.info("Getting breakdown status")
        
        # Initialize alert service
        alert_service = VehicleAlertService(db)
        
        # Get broken vehicles data
        broken_vehicles = alert_service.get_broken_vehicles_with_contacts()
        
        return VehicleAlertResponse(
            success=True,
            message=f"Found {len(broken_vehicles)} broken vehicle(s)",
            vehicles_count=len(broken_vehicles),
            alerts_sent=0,
            vehicles_data=broken_vehicles
        )
        
    except Exception as e:
        logger.exception("Error getting breakdown status", exc_info=e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get breakdown status: {str(e)}"
        )


@router.get("/health", response_model=VehicleAPIHealthResponse)
async def vehicle_api_health(
    service: VehicleAPIService = Depends(get_vehicle_service),
):
    """
    Health check endpoint for vehicle API integration

    Returns:
        VehicleAPIHealthResponse with health status and metrics
    """
    try:
        health_status = await service.health_check()
        return health_status
    except Exception as e:
        logger.exception("Health check failed", exc_info=e)
        raise HTTPException(
            status_code=503,
            detail=f"Health check failed: {str(e)}",
        )


@router.get("/not-working", response_model=NotWorkingVehiclesResponse)
async def get_not_working_vehicles(
    service: VehicleAPIService = Depends(get_vehicle_service),
):
    """
    Get list of all not working vehicles

    Returns:
        NotWorkingVehiclesResponse with list of not working vehicles
    """
    try:
        result = await service.get_not_working_vehicles()
        return result
    except VehicleAPIAuthenticationError as e:
        logger.error("Authentication failed for not working vehicles", extra={"error": str(e)})
        raise HTTPException(
            status_code=401,
            detail="Vehicle API authentication failed",
        )
    except VehicleAPITimeoutError as e:
        logger.error("Timeout fetching not working vehicles", extra={"error": str(e)})
        raise HTTPException(
            status_code=504,
            detail="Vehicle API request timeout",
        )
    except VehicleAPIConnectionError as e:
        logger.error("Connection error fetching not working vehicles", extra={"error": str(e)})
        raise HTTPException(
            status_code=503,
            detail="Vehicle API connection error",
        )
    except VehicleAPIException as e:
        logger.error("Error fetching not working vehicles", extra={"error": str(e)})
        raise HTTPException(
            status_code=500,
            detail=f"Vehicle API error: {str(e)}",
        )
    except Exception as e:
        logger.exception("Unexpected error fetching not working vehicles", exc_info=e)
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


@router.get("/search", response_model=VehicleSearchResponse)
async def search_vehicle(
    vehicle_number: str = Query(..., description="Vehicle registration number"),
    service: VehicleAPIService = Depends(get_vehicle_service),
):
    """
    Search for a vehicle by registration number

    Args:
        vehicle_number: Vehicle registration number

    Returns:
        VehicleSearchResponse with basic vehicle information
    """
    try:
        result = await service.search_vehicle(vehicle_number)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Vehicle {vehicle_number} not found",
            )

        return result
    except HTTPException:
        raise
    except VehicleAPIAuthenticationError as e:
        logger.error("Authentication failed for vehicle search", extra={"error": str(e)})
        raise HTTPException(
            status_code=401,
            detail="Vehicle API authentication failed",
        )
    except VehicleAPITimeoutError as e:
        logger.error("Timeout searching vehicle", extra={"error": str(e)})
        raise HTTPException(
            status_code=504,
            detail="Vehicle API request timeout",
        )
    except VehicleAPIConnectionError as e:
        logger.error("Connection error searching vehicle", extra={"error": str(e)})
        raise HTTPException(
            status_code=503,
            detail="Vehicle API connection error",
        )
    except VehicleAPIException as e:
        logger.error("Error searching vehicle", extra={"error": str(e)})
        raise HTTPException(
            status_code=500,
            detail=f"Vehicle API error: {str(e)}",
        )
    except Exception as e:
        logger.exception("Unexpected error searching vehicle", exc_info=e)
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


@router.get("/{vehicle_number}", response_model=VehicleDetails)
async def get_vehicle_details(
    vehicle_number: str,
    service: VehicleAPIService = Depends(get_vehicle_service),
):
    """
    Get complete vehicle details by registration number

    Args:
        vehicle_number: Vehicle registration number

    Returns:
        VehicleDetails with complete vehicle information
    """
    try:
        result = await service.get_vehicle_details(vehicle_number)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Vehicle {vehicle_number} not found",
            )

        return result
    except HTTPException:
        raise
    except VehicleAPIAuthenticationError as e:
        logger.error("Authentication failed for vehicle details", extra={"error": str(e)})
        raise HTTPException(
            status_code=401,
            detail="Vehicle API authentication failed",
        )
    except VehicleAPITimeoutError as e:
        logger.error("Timeout fetching vehicle details", extra={"error": str(e)})
        raise HTTPException(
            status_code=504,
            detail="Vehicle API request timeout",
        )
    except VehicleAPIConnectionError as e:
        logger.error("Connection error fetching vehicle details", extra={"error": str(e)})
        raise HTTPException(
            status_code=503,
            detail="Vehicle API connection error",
        )
    except VehicleAPIException as e:
        logger.error("Error fetching vehicle details", extra={"error": str(e)})
        raise HTTPException(
            status_code=500,
            detail=f"Vehicle API error: {str(e)}",
        )
    except Exception as e:
        logger.exception("Unexpected error fetching vehicle details", exc_info=e)
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


@router.get("/{vehicle_number}/status", response_model=VehicleStatusResponse)
async def get_vehicle_status(
    vehicle_number: str,
    service: VehicleAPIService = Depends(get_vehicle_service),
):
    """
    Get vehicle status only

    Args:
        vehicle_number: Vehicle registration number

    Returns:
        VehicleStatusResponse with vehicle status
    """
    try:
        result = await service.get_vehicle_status(vehicle_number)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Vehicle {vehicle_number} not found",
            )

        return result
    except HTTPException:
        raise
    except VehicleAPIAuthenticationError as e:
        logger.error("Authentication failed for vehicle status", extra={"error": str(e)})
        raise HTTPException(
            status_code=401,
            detail="Vehicle API authentication failed",
        )
    except VehicleAPITimeoutError as e:
        logger.error("Timeout fetching vehicle status", extra={"error": str(e)})
        raise HTTPException(
            status_code=504,
            detail="Vehicle API request timeout",
        )
    except VehicleAPIConnectionError as e:
        logger.error("Connection error fetching vehicle status", extra={"error": str(e)})
        raise HTTPException(
            status_code=503,
            detail="Vehicle API connection error",
        )
    except VehicleAPIException as e:
        logger.error("Error fetching vehicle status", extra={"error": str(e)})
        raise HTTPException(
            status_code=500,
            detail=f"Vehicle API error: {str(e)}",
        )
    except Exception as e:
        logger.exception("Unexpected error fetching vehicle status", exc_info=e)
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


@router.get("/{vehicle_number}/location", response_model=VehicleLocationResponse)
async def get_vehicle_location(
    vehicle_number: str,
    service: VehicleAPIService = Depends(get_vehicle_service),
):
    """
    Get vehicle location only

    Args:
        vehicle_number: Vehicle registration number

    Returns:
        VehicleLocationResponse with vehicle location
    """
    try:
        result = await service.get_vehicle_location(vehicle_number)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Vehicle {vehicle_number} not found",
            )

        return result
    except HTTPException:
        raise
    except VehicleAPIAuthenticationError as e:
        logger.error("Authentication failed for vehicle location", extra={"error": str(e)})
        raise HTTPException(
            status_code=401,
            detail="Vehicle API authentication failed",
        )
    except VehicleAPITimeoutError as e:
        logger.error("Timeout fetching vehicle location", extra={"error": str(e)})
        raise HTTPException(
            status_code=504,
            detail="Vehicle API request timeout",
        )
    except VehicleAPIConnectionError as e:
        logger.error("Connection error fetching vehicle location", extra={"error": str(e)})
        raise HTTPException(
            status_code=503,
            detail="Vehicle API connection error",
        )
    except VehicleAPIException as e:
        logger.error("Error fetching vehicle location", extra={"error": str(e)})
        raise HTTPException(
            status_code=500,
            detail=f"Vehicle API error: {str(e)}",
        )
    except Exception as e:
        logger.exception("Unexpected error fetching vehicle location", exc_info=e)
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )
