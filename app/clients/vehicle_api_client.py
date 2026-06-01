"""
Vehicle API HTTP Client
Handles all HTTP communication with external vehicle tracking API
"""
import logging
import time
from typing import Any, Dict, Optional

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from app.core.config import (
    VEHICLE_API_BASE_URL,
    VEHICLE_API_USERNAME,
    VEHICLE_API_PASSWORD,
    VEHICLE_API_TIMEOUT,
    VEHICLE_API_MAX_RETRIES,
    VEHICLE_API_RETRY_DELAY,
)

logger = logging.getLogger("app.vehicle_api_client")


class VehicleAPIException(Exception):
    """Base exception for vehicle API errors"""
    pass


class VehicleAPIConnectionError(VehicleAPIException):
    """Connection error to vehicle API"""
    pass


class VehicleAPITimeoutError(VehicleAPIException):
    """Timeout error from vehicle API"""
    pass


class VehicleAPIAuthenticationError(VehicleAPIException):
    """Authentication error with vehicle API"""
    pass


class VehicleAPIRateLimitError(VehicleAPIException):
    """Rate limit error from vehicle API"""
    pass


class VehicleAPIServerError(VehicleAPIException):
    """Server error from vehicle API"""
    pass


class VehicleAPIInvalidResponseError(VehicleAPIException):
    """Invalid response from vehicle API"""
    pass


class VehicleAPIClient:
    """
    HTTP client for vehicle tracking API with connection pooling,
    retry logic, and comprehensive error handling
    """

    def __init__(
        self,
        base_url: str = VEHICLE_API_BASE_URL,
        username: str = VEHICLE_API_USERNAME,
        password: str = VEHICLE_API_PASSWORD,
        timeout: int = VEHICLE_API_TIMEOUT,
        max_retries: int = VEHICLE_API_MAX_RETRIES,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self.max_retries = max_retries

        # Connection pooling configuration
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0,
        )

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            limits=limits,
            follow_redirects=True,
        )

        logger.info(
            "VehicleAPIClient initialized",
            extra={
                "base_url": self.base_url,
                "timeout": self.timeout,
                "max_retries": self.max_retries,
            },
        )

    async def close(self):
        """Close the HTTP client connection pool"""
        await self.client.aclose()
        logger.info("VehicleAPIClient closed")

    def _get_auth_payload(self) -> Dict[str, str]:
        """Get authentication payload for API requests"""
        if not self.username or not self.password:
            logger.error("Vehicle API credentials not configured")
            raise VehicleAPIAuthenticationError("Vehicle API credentials not configured")

        return {
            "username": self.username,
            "password": self.password,
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic and error handling

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON request body

        Returns:
            Parsed JSON response

        Raises:
            VehicleAPIException: On various API errors
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        start_time = time.time()

        try:
            logger.info(
                "Making vehicle API request",
                extra={
                    "method": method,
                    "url": url,
                    "params": params,
                },
            )

            response = await self.client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
            )

            elapsed_ms = (time.time() - start_time) * 1000

            logger.info(
                "Vehicle API response received",
                extra={
                    "method": method,
                    "url": url,
                    "status_code": response.status_code,
                    "elapsed_ms": round(elapsed_ms, 2),
                },
            )

            # Handle different status codes
            if response.status_code == 200:
                try:
                    return response.json()
                except Exception as e:
                    logger.error(
                        "Failed to parse vehicle API response",
                        extra={"url": url, "error": str(e)},
                    )
                    raise VehicleAPIInvalidResponseError(f"Invalid JSON response: {str(e)}")

            elif response.status_code == 401 or response.status_code == 403:
                logger.error(
                    "Vehicle API authentication failed",
                    extra={"url": url, "status_code": response.status_code},
                )
                raise VehicleAPIAuthenticationError(
                    f"Authentication failed with status {response.status_code}"
                )

            elif response.status_code == 429:
                logger.warning(
                    "Vehicle API rate limit exceeded",
                    extra={"url": url},
                )
                raise VehicleAPIRateLimitError("Rate limit exceeded")

            elif response.status_code >= 500:
                logger.error(
                    "Vehicle API server error",
                    extra={"url": url, "status_code": response.status_code},
                )
                raise VehicleAPIServerError(
                    f"Server error with status {response.status_code}"
                )

            else:
                logger.error(
                    "Vehicle API unexpected status code",
                    extra={"url": url, "status_code": response.status_code},
                )
                raise VehicleAPIException(
                    f"Unexpected status code {response.status_code}"
                )

        except httpx.TimeoutException as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(
                "Vehicle API request timeout",
                extra={
                    "url": url,
                    "timeout": self.timeout,
                    "elapsed_ms": round(elapsed_ms, 2),
                },
            )
            raise VehicleAPITimeoutError(f"Request timeout after {self.timeout}s") from e

        except httpx.ConnectError as e:
            logger.error(
                "Vehicle API connection error",
                extra={"url": url, "error": str(e)},
            )
            raise VehicleAPIConnectionError(f"Connection error: {str(e)}") from e

        except (VehicleAPIException, VehicleAPIAuthenticationError, VehicleAPIRateLimitError, VehicleAPIServerError):
            # Re-raise our custom exceptions
            raise

        except Exception as e:
            logger.exception(
                "Unexpected error in vehicle API request",
                extra={"url": url},
                exc_info=e,
            )
            raise VehicleAPIException(f"Unexpected error: {str(e)}") from e

    async def get_list_vehicles(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get list of vehicles from API

        Args:
            params: Optional query parameters

        Returns:
            API response with vehicle list
        """
        auth_params = self._get_auth_payload()
        if params:
            auth_params.update(params)

        return await self._make_request("GET", "getListVehiclesmob", params=auth_params)

    async def health_check(self) -> tuple[bool, Optional[float]]:
        """
        Perform health check on vehicle API

        Returns:
            Tuple of (is_healthy, response_time_ms)
        """
        start_time = time.time()
        try:
            await self.get_list_vehicles()
            elapsed_ms = (time.time() - start_time) * 1000
            logger.info("Vehicle API health check passed", extra={"elapsed_ms": round(elapsed_ms, 2)})
            return True, elapsed_ms
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(
                "Vehicle API health check failed",
                extra={"error": str(e), "elapsed_ms": round(elapsed_ms, 2)},
            )
            return False, elapsed_ms
