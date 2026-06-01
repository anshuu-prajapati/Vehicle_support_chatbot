"""
Unit tests for Vehicle API Client
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.clients.vehicle_api_client import (
    VehicleAPIClient,
    VehicleAPIException,
    VehicleAPIConnectionError,
    VehicleAPITimeoutError,
    VehicleAPIAuthenticationError,
    VehicleAPIRateLimitError,
    VehicleAPIServerError,
    VehicleAPIInvalidResponseError,
)


@pytest.fixture
def mock_client():
    """Fixture for VehicleAPIClient with mocked httpx client"""
    with patch("app.clients.vehicle_api_client.httpx.AsyncClient") as mock:
        client = VehicleAPIClient(
            base_url="https://test.api.com",
            username="test_user",
            password="test_pass",
            timeout=10,
        )
        client.client = AsyncMock()
        yield client


@pytest.mark.asyncio
async def test_get_list_vehicles_success(mock_client):
    """Test successful vehicle list retrieval"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"vehicle_number": "DL01AB1234", "status": "online"}
        ]
    }
    mock_client.client.request = AsyncMock(return_value=mock_response)

    result = await mock_client.get_list_vehicles()

    assert result["data"][0]["vehicle_number"] == "DL01AB1234"
    assert result["data"][0]["status"] == "online"


@pytest.mark.asyncio
async def test_authentication_error(mock_client):
    """Test authentication error handling"""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_client.client.request = AsyncMock(return_value=mock_response)

    with pytest.raises(VehicleAPIAuthenticationError):
        await mock_client.get_list_vehicles()


@pytest.mark.asyncio
async def test_rate_limit_error(mock_client):
    """Test rate limit error handling"""
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_client.client.request = AsyncMock(return_value=mock_response)

    with pytest.raises(VehicleAPIRateLimitError):
        await mock_client.get_list_vehicles()


@pytest.mark.asyncio
async def test_server_error(mock_client):
    """Test server error handling"""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_client.client.request = AsyncMock(return_value=mock_response)

    with pytest.raises(VehicleAPIServerError):
        await mock_client.get_list_vehicles()


@pytest.mark.asyncio
async def test_timeout_error(mock_client):
    """Test timeout error handling"""
    mock_client.client.request = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

    with pytest.raises(VehicleAPITimeoutError):
        await mock_client.get_list_vehicles()


@pytest.mark.asyncio
async def test_connection_error(mock_client):
    """Test connection error handling"""
    mock_client.client.request = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))

    with pytest.raises(VehicleAPIConnectionError):
        await mock_client.get_list_vehicles()


@pytest.mark.asyncio
async def test_invalid_json_response(mock_client):
    """Test invalid JSON response handling"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_client.client.request = AsyncMock(return_value=mock_response)

    with pytest.raises(VehicleAPIInvalidResponseError):
        await mock_client.get_list_vehicles()


@pytest.mark.asyncio
async def test_health_check_success(mock_client):
    """Test successful health check"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": []}
    mock_client.client.request = AsyncMock(return_value=mock_response)

    is_healthy, response_time = await mock_client.health_check()

    assert is_healthy is True
    assert response_time is not None
    assert response_time > 0


@pytest.mark.asyncio
async def test_health_check_failure(mock_client):
    """Test failed health check"""
    mock_client.client.request = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))

    is_healthy, response_time = await mock_client.health_check()

    assert is_healthy is False
    assert response_time is not None


@pytest.mark.asyncio
async def test_missing_credentials():
    """Test missing credentials error"""
    with patch("app.clients.vehicle_api_client.httpx.AsyncClient"):
        client = VehicleAPIClient(
            base_url="https://test.api.com",
            username=None,
            password=None,
        )
        client.client = AsyncMock()

        with pytest.raises(VehicleAPIAuthenticationError):
            await client.get_list_vehicles()


@pytest.mark.asyncio
async def test_close_client(mock_client):
    """Test client closure"""
    await mock_client.close()
    mock_client.client.aclose.assert_called_once()
