"""
Vehicle API Service Layer
Business logic for vehicle operations with caching and data normalization
"""
import json
import logging
from datetime import datetime
from typing import List, Optional

from app.clients.vehicle_api_client import VehicleAPIClient, VehicleAPIException
from app.schemas.vehicle_schema import (
    VehicleDetails,
    VehicleLocation,
    VehicleStatus,
    VehicleStatusResponse,
    VehicleLocationResponse,
    VehicleSearchResponse,
    NotWorkingVehiclesResponse,
    VehicleAPIHealthResponse,
)
from app.core.config import REDIS_ENABLED, VEHICLE_CACHE_TTL

logger = logging.getLogger("app.vehicle_api_service")


class VehicleAPIService:
    """
    Service layer for vehicle API operations
    Handles business logic, caching, and data normalization
    """

    def __init__(self, client: Optional[VehicleAPIClient] = None, cache_client=None):
        """
        Initialize vehicle API service

        Args:
            client: VehicleAPIClient instance (created if not provided)
            cache_client: Optional Redis cache client
        """
        self.client = client or VehicleAPIClient()
        self.cache_client = cache_client
        self.cache_enabled = REDIS_ENABLED and cache_client is not None

        logger.info(
            "VehicleAPIService initialized",
            extra={"cache_enabled": self.cache_enabled},
        )

    async def close(self):
        """Close service connections"""
        if self.client:
            await self.client.close()

    def _normalize_status(self, raw_status: Optional[str]) -> VehicleStatus:
        """
        Normalize vehicle status from API response

        Args:
            raw_status: Raw status string from API

        Returns:
            Normalized VehicleStatus enum
        """
        if not raw_status:
            return VehicleStatus.UNKNOWN

        status_lower = str(raw_status).lower().strip()

        # Map various status strings to normalized enum
        if status_lower in ["online", "active", "running", "working"]:
            return VehicleStatus.ONLINE
        elif status_lower in ["offline", "inactive", "stopped"]:
            return VehicleStatus.OFFLINE
        elif status_lower in ["not_working", "notworking", "not working", "broken", "faulty"]:
            return VehicleStatus.NOT_WORKING
        else:
            logger.warning(
                "Unknown vehicle status encountered",
                extra={"raw_status": raw_status},
            )
            return VehicleStatus.UNKNOWN

    def _parse_vehicle_data(self, raw_data: dict) -> VehicleDetails:
        """
        Parse and normalize raw vehicle data from API

        Args:
            raw_data: Raw vehicle data from API

        Returns:
            Normalized VehicleDetails object
        """
        # Extract location data
        location = None
        if raw_data.get("latitude") or raw_data.get("longitude"):
            location = VehicleLocation(
                latitude=raw_data.get("latitude"),
                longitude=raw_data.get("longitude"),
                address=raw_data.get("address") or raw_data.get("location"),
                last_update=self._parse_datetime(raw_data.get("last_location_update")),
            )

        # Parse last update time
        last_update = self._parse_datetime(
            raw_data.get("last_update") or raw_data.get("updated_at")
        )

        return VehicleDetails(
            vehicle_number=raw_data.get("vehicle_number", ""),
            imei=raw_data.get("imei") or raw_data.get("device_id"),
            status=self._normalize_status(raw_data.get("status")),
            last_location=location,
            last_update_time=last_update,
            owner_name=raw_data.get("owner_name"),
            owner_phone=raw_data.get("owner_phone") or raw_data.get("owner_contact"),
            driver_name=raw_data.get("driver_name"),
            driver_phone=raw_data.get("driver_phone") or raw_data.get("driver_contact"),
            raw_data=raw_data,
        )

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """
        Parse datetime string from API

        Args:
            dt_str: Datetime string

        Returns:
            Parsed datetime or None
        """
        if not dt_str:
            return None

        try:
            # Try common datetime formats
            for fmt in [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%d",
            ]:
                try:
                    return datetime.strptime(dt_str, fmt)
                except ValueError:
                    continue

            # If no format matches, log warning
            logger.warning(
                "Failed to parse datetime string",
                extra={"datetime_str": dt_str},
            )
            return None

        except Exception as e:
            logger.error(
                "Error parsing datetime",
                extra={"datetime_str": dt_str, "error": str(e)},
            )
            return None

    async def _get_from_cache(self, cache_key: str) -> Optional[dict]:
        """Get data from Redis cache"""
        if not self.cache_enabled:
            return None

        try:
            cached_data = await self.cache_client.get(cache_key)
            if cached_data:
                logger.debug("Cache hit", extra={"cache_key": cache_key})
                return json.loads(cached_data)
            logger.debug("Cache miss", extra={"cache_key": cache_key})
            return None
        except Exception as e:
            logger.warning(
                "Cache read error, continuing without cache",
                extra={"cache_key": cache_key, "error": str(e)},
            )
            return None

    async def _set_to_cache(self, cache_key: str, data: dict, ttl: int = VEHICLE_CACHE_TTL):
        """Set data to Redis cache"""
        if not self.cache_enabled:
            return

        try:
            await self.cache_client.setex(
                cache_key,
                ttl,
                json.dumps(data, default=str),
            )
            logger.debug("Cache set", extra={"cache_key": cache_key, "ttl": ttl})
        except Exception as e:
            logger.warning(
                "Cache write error, continuing without cache",
                extra={"cache_key": cache_key, "error": str(e)},
            )

    async def get_vehicle_details(self, vehicle_number: str) -> Optional[VehicleDetails]:
        """
        Get complete vehicle details by vehicle number

        Args:
            vehicle_number: Vehicle registration number

        Returns:
            VehicleDetails object or None if not found
        """
        normalized_number = vehicle_number.strip().upper().replace(" ", "")
        cache_key = f"vehicle:details:{normalized_number}"

        logger.info(
            "Fetching vehicle details",
            extra={"vehicle_number": normalized_number},
        )

        # Try cache first
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            return VehicleDetails(**cached_data)

        try:
            # Fetch from API
            response = await self.client.get_list_vehicles()

            # Parse response and find vehicle
            vehicles = response.get("data", []) or response.get("vehicles", [])

            for vehicle_data in vehicles:
                if vehicle_data.get("vehicle_number", "").strip().upper().replace(" ", "") == normalized_number:
                    vehicle_details = self._parse_vehicle_data(vehicle_data)

                    # Cache the result
                    await self._set_to_cache(cache_key, vehicle_details.dict())

                    logger.info(
                        "Vehicle details found",
                        extra={
                            "vehicle_number": normalized_number,
                            "status": vehicle_details.status,
                        },
                    )
                    return vehicle_details

            logger.warning(
                "Vehicle not found",
                extra={"vehicle_number": normalized_number},
            )
            return None

        except VehicleAPIException as e:
            logger.error(
                "Failed to fetch vehicle details",
                extra={"vehicle_number": normalized_number, "error": str(e)},
            )
            raise

    async def get_vehicle_status(self, vehicle_number: str) -> Optional[VehicleStatusResponse]:
        """
        Get vehicle status only

        Args:
            vehicle_number: Vehicle registration number

        Returns:
            VehicleStatusResponse or None if not found
        """
        vehicle_details = await self.get_vehicle_details(vehicle_number)

        if not vehicle_details:
            return None

        return VehicleStatusResponse(
            vehicle_number=vehicle_details.vehicle_number,
            status=vehicle_details.status,
            last_update_time=vehicle_details.last_update_time,
        )

    async def get_vehicle_location(self, vehicle_number: str) -> Optional[VehicleLocationResponse]:
        """
        Get vehicle location only

        Args:
            vehicle_number: Vehicle registration number

        Returns:
            VehicleLocationResponse or None if not found
        """
        vehicle_details = await self.get_vehicle_details(vehicle_number)

        if not vehicle_details:
            return None

        return VehicleLocationResponse(
            vehicle_number=vehicle_details.vehicle_number,
            location=vehicle_details.last_location,
            status=vehicle_details.status,
        )

    async def search_vehicle(self, vehicle_number: str) -> Optional[VehicleSearchResponse]:
        """
        Search for vehicle with basic information

        Args:
            vehicle_number: Vehicle registration number

        Returns:
            VehicleSearchResponse or None if not found
        """
        vehicle_details = await self.get_vehicle_details(vehicle_number)

        if not vehicle_details:
            return None

        return VehicleSearchResponse(
            vehicle_number=vehicle_details.vehicle_number,
            status=vehicle_details.status,
            owner_name=vehicle_details.owner_name,
            last_update_time=vehicle_details.last_update_time,
        )

    async def get_not_working_vehicles(self) -> NotWorkingVehiclesResponse:
        """
        Get list of all not working vehicles

        Returns:
            NotWorkingVehiclesResponse with list of not working vehicles
        """
        cache_key = "vehicles:not_working"

        logger.info("Fetching not working vehicles")

        # Try cache first
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            return NotWorkingVehiclesResponse(**cached_data)

        try:
            # Fetch from API
            response = await self.client.get_list_vehicles()

            # Parse response
            vehicles = response.get("data", []) or response.get("vehicles", [])

            not_working_vehicles = []
            for vehicle_data in vehicles:
                status = self._normalize_status(vehicle_data.get("status"))

                if status == VehicleStatus.NOT_WORKING:
                    not_working_vehicles.append(
                        VehicleSearchResponse(
                            vehicle_number=vehicle_data.get("vehicle_number", ""),
                            status=status,
                            owner_name=vehicle_data.get("owner_name"),
                            last_update_time=self._parse_datetime(
                                vehicle_data.get("last_update") or vehicle_data.get("updated_at")
                            ),
                        )
                    )

            result = NotWorkingVehiclesResponse(
                total_count=len(not_working_vehicles),
                vehicles=not_working_vehicles,
            )

            # Cache the result with shorter TTL
            await self._set_to_cache(cache_key, result.dict(), ttl=60)

            logger.info(
                "Not working vehicles fetched",
                extra={"count": result.total_count},
            )

            return result

        except VehicleAPIException as e:
            logger.error(
                "Failed to fetch not working vehicles",
                extra={"error": str(e)},
            )
            raise

    async def health_check(self) -> VehicleAPIHealthResponse:
        """
        Perform health check on vehicle API and cache

        Returns:
            VehicleAPIHealthResponse with health status
        """
        logger.info("Performing vehicle API health check")

        # Check external API
        api_healthy, response_time = await self.client.health_check()

        # Check cache
        cache_healthy = False
        if self.cache_enabled:
            try:
                await self.cache_client.ping()
                cache_healthy = True
            except Exception as e:
                logger.warning("Cache health check failed", extra={"error": str(e)})

        # Determine overall status
        if api_healthy and (cache_healthy or not self.cache_enabled):
            status = "healthy"
        elif api_healthy:
            status = "degraded"
        else:
            status = "unhealthy"

        return VehicleAPIHealthResponse(
            status=status,
            external_api_reachable=api_healthy,
            response_time_ms=response_time,
            cache_enabled=self.cache_enabled,
            cache_healthy=cache_healthy,
        )
