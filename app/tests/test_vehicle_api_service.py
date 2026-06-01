"""
Unit tests for Vehicle API Service
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.vehicle_api_service import VehicleAPIService
from app.schemas.vehicle_schema import VehicleStatus, VehicleDetails


@pytest.fixture
def mock_vehicle_service():
    """Fixture for VehicleAPIService with mocked client"""
    mock_client = AsyncMock()
    service = VehicleAPIService(client=mock_client, cache_client=None)
    return service


@pytest.fixture
def sample_vehicle_data():
    """Sample vehicle data from API"""
    return {
        "vehicle_number": "DL01AB1234",
        "imei": "123456789012345",
        "status": "not_working",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "address": "Delhi NCR",
        "owner_name": "John Doe",
        "owner_phone": "9876543210",
        "driver_name": "Driver Name",
        "driver_phone": "9876543211",
        "last_update": "2024-01-15 10:30:00",
    }


@pytest.mark.asyncio
async def test_normalize_status_online(mock_vehicle_service):
    """Test status normalization for online status"""
    assert mock_vehicle_service._normalize_status("online") == VehicleStatus.ONLINE
    assert mock_vehicle_service._normalize_status("ONLINE") == VehicleStatus.ONLINE
    assert mock_vehicle_service._normalize_status("active") == VehicleStatus.ONLINE
    assert mock_vehicle_service._normalize_status("running") == VehicleStatus.ONLINE


@pytest.mark.asyncio
async def test_normalize_status_offline(mock_vehicle_service):
    """Test status normalization for offline status"""
    assert mock_vehicle_service._normalize_status("offline") == VehicleStatus.OFFLINE
    assert mock_vehicle_service._normalize_status("OFFLINE") == VehicleStatus.OFFLINE
    assert mock_vehicle_service._normalize_status("inactive") == VehicleStatus.OFFLINE


@pytest.mark.asyncio
async def test_normalize_status_not_working(mock_vehicle_service):
    """Test status normalization for not working status"""
    assert mock_vehicle_service._normalize_status("not_working") == VehicleStatus.NOT_WORKING
    assert mock_vehicle_service._normalize_status("NOT WORKING") == VehicleStatus.NOT_WORKING
    assert mock_vehicle_service._normalize_status("broken") == VehicleStatus.NOT_WORKING


@pytest.mark.asyncio
async def test_normalize_status_unknown(mock_vehicle_service):
    """Test status normalization for unknown status"""
    assert mock_vehicle_service._normalize_status("") == VehicleStatus.UNKNOWN
    assert mock_vehicle_service._normalize_status(None) == VehicleStatus.UNKNOWN
    assert mock_vehicle_service._normalize_status("invalid") == VehicleStatus.UNKNOWN


@pytest.mark.asyncio
async def test_parse_vehicle_data(mock_vehicle_service, sample_vehicle_data):
    """Test vehicle data parsing"""
    vehicle = mock_vehicle_service._parse_vehicle_data(sample_vehicle_data)

    assert vehicle.vehicle_number == "DL01AB1234"
    assert vehicle.imei == "123456789012345"
    assert vehicle.status == VehicleStatus.NOT_WORKING
    assert vehicle.owner_name == "John Doe"
    assert vehicle.owner_phone == "9876543210"
    assert vehicle.last_location is not None
    assert vehicle.last_location.latitude == 28.6139
    assert vehicle.last_location.longitude == 77.2090
    assert vehicle.last_location.address == "Delhi NCR"


@pytest.mark.asyncio
async def test_get_vehicle_details_found(mock_vehicle_service, sample_vehicle_data):
    """Test getting vehicle details when vehicle is found"""
    mock_vehicle_service.client.get_list_vehicles = AsyncMock(
        return_value={"data": [sample_vehicle_data]}
    )

    result = await mock_vehicle_service.get_vehicle_details("DL01AB1234")

    assert result is not None
    assert result.vehicle_number == "DL01AB1234"
    assert result.status == VehicleStatus.NOT_WORKING


@pytest.mark.asyncio
async def test_get_vehicle_details_not_found(mock_vehicle_service):
    """Test getting vehicle details when vehicle is not found"""
    mock_vehicle_service.client.get_list_vehicles = AsyncMock(
        return_value={"data": []}
    )

    result = await mock_vehicle_service.get_vehicle_details("NOTFOUND")

    assert result is None


@pytest.mark.asyncio
async def test_get_vehicle_details_case_insensitive(mock_vehicle_service, sample_vehicle_data):
    """Test vehicle search is case insensitive"""
    mock_vehicle_service.client.get_list_vehicles = AsyncMock(
        return_value={"data": [sample_vehicle_data]}
    )

    result = await mock_vehicle_service.get_vehicle_details("dl01ab1234")

    assert result is not None
    assert result.vehicle_number == "DL01AB1234"


@pytest.mark.asyncio
async def test_get_vehicle_status(mock_vehicle_service, sample_vehicle_data):
    """Test getting vehicle status"""
    mock_vehicle_service.client.get_list_vehicles = AsyncMock(
        return_value={"data": [sample_vehicle_data]}
    )

    result = await mock_vehicle_service.get_vehicle_status("DL01AB1234")

    assert result is not None
    assert result.vehicle_number == "DL01AB1234"
    assert result.status == VehicleStatus.NOT_WORKING


@pytest.mark.asyncio
async def test_get_vehicle_location(mock_vehicle_service, sample_vehicle_data):
    """Test getting vehicle location"""
    mock_vehicle_service.client.get_list_vehicles = AsyncMock(
        return_value={"data": [sample_vehicle_data]}
    )

    result = await mock_vehicle_service.get_vehicle_location("DL01AB1234")

    assert result is not None
    assert result.vehicle_number == "DL01AB1234"
    assert result.location is not None
    assert result.location.address == "Delhi NCR"


@pytest.mark.asyncio
async def test_search_vehicle(mock_vehicle_service, sample_vehicle_data):
    """Test vehicle search"""
    mock_vehicle_service.client.get_list_vehicles = AsyncMock(
        return_value={"data": [sample_vehicle_data]}
    )

    result = await mock_vehicle_service.search_vehicle("DL01AB1234")

    assert result is not None
    assert result.vehicle_number == "DL01AB1234"
    assert result.status == VehicleStatus.NOT_WORKING
    assert result.owner_name == "John Doe"


@pytest.mark.asyncio
async def test_get_not_working_vehicles(mock_vehicle_service):
    """Test getting not working vehicles"""
    mock_data = [
        {"vehicle_number": "DL01AB1234", "status": "not_working", "owner_name": "Owner 1"},
        {"vehicle_number": "DL02CD5678", "status": "online", "owner_name": "Owner 2"},
        {"vehicle_number": "DL03EF9012", "status": "not_working", "owner_name": "Owner 3"},
    ]

    mock_vehicle_service.client.get_list_vehicles = AsyncMock(
        return_value={"data": mock_data}
    )

    result = await mock_vehicle_service.get_not_working_vehicles()

    assert result.total_count == 2
    assert len(result.vehicles) == 2
    assert result.vehicles[0].vehicle_number == "DL01AB1234"
    assert result.vehicles[1].vehicle_number == "DL03EF9012"


@pytest.mark.asyncio
async def test_get_not_working_vehicles_empty(mock_vehicle_service):
    """Test getting not working vehicles when none exist"""
    mock_data = [
        {"vehicle_number": "DL01AB1234", "status": "online", "owner_name": "Owner 1"},
    ]

    mock_vehicle_service.client.get_list_vehicles = AsyncMock(
        return_value={"data": mock_data}
    )

    result = await mock_vehicle_service.get_not_working_vehicles()

    assert result.total_count == 0
    assert len(result.vehicles) == 0


@pytest.mark.asyncio
async def test_health_check_healthy(mock_vehicle_service):
    """Test health check when API is healthy"""
    mock_vehicle_service.client.health_check = AsyncMock(return_value=(True, 120.5))

    result = await mock_vehicle_service.health_check()

    assert result.status == "healthy"
    assert result.external_api_reachable is True
    assert result.response_time_ms == 120.5


@pytest.mark.asyncio
async def test_health_check_unhealthy(mock_vehicle_service):
    """Test health check when API is unhealthy"""
    mock_vehicle_service.client.health_check = AsyncMock(return_value=(False, 5000.0))

    result = await mock_vehicle_service.health_check()

    assert result.status == "unhealthy"
    assert result.external_api_reachable is False


@pytest.mark.asyncio
async def test_parse_datetime_valid(mock_vehicle_service):
    """Test datetime parsing with valid formats"""
    dt1 = mock_vehicle_service._parse_datetime("2024-01-15 10:30:00")
    assert dt1 is not None
    assert dt1.year == 2024
    assert dt1.month == 1
    assert dt1.day == 15

    dt2 = mock_vehicle_service._parse_datetime("2024-01-15T10:30:00")
    assert dt2 is not None

    dt3 = mock_vehicle_service._parse_datetime("2024-01-15")
    assert dt3 is not None


@pytest.mark.asyncio
async def test_parse_datetime_invalid(mock_vehicle_service):
    """Test datetime parsing with invalid formats"""
    dt1 = mock_vehicle_service._parse_datetime("invalid")
    assert dt1 is None

    dt2 = mock_vehicle_service._parse_datetime("")
    assert dt2 is None

    dt3 = mock_vehicle_service._parse_datetime(None)
    assert dt3 is None
