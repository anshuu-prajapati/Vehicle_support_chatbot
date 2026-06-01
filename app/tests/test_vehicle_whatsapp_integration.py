"""
Unit tests for Vehicle WhatsApp Integration
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.services.vehicle_whatsapp_integration import VehicleWhatsAppIntegration
from app.schemas.vehicle_schema import VehicleDetails, VehicleStatus, VehicleLocation


@pytest.fixture
def mock_integration():
    """Fixture for VehicleWhatsAppIntegration with mocked service"""
    mock_service = AsyncMock()
    integration = VehicleWhatsAppIntegration(vehicle_service=mock_service)
    return integration


@pytest.fixture
def sample_vehicle_details():
    """Sample vehicle details"""
    return VehicleDetails(
        vehicle_number="DL01AB1234",
        imei="123456789012345",
        status=VehicleStatus.NOT_WORKING,
        last_location=VehicleLocation(
            latitude=28.6139,
            longitude=77.2090,
            address="Delhi NCR",
            last_update=datetime(2024, 1, 15, 10, 30),
        ),
        last_update_time=datetime(2024, 1, 15, 10, 30),
        owner_name="John Doe",
        owner_phone="9876543210",
        driver_name="Driver Name",
        driver_phone="9876543211",
    )


@pytest.mark.asyncio
async def test_validate_and_fetch_vehicle_found(mock_integration, sample_vehicle_details):
    """Test vehicle validation when vehicle is found"""
    mock_integration.vehicle_service.get_vehicle_details = AsyncMock(
        return_value=sample_vehicle_details
    )

    is_valid, message, vehicle = await mock_integration.validate_and_fetch_vehicle("DL01AB1234")

    assert is_valid is True
    assert vehicle is not None
    assert vehicle.vehicle_number == "DL01AB1234"
    assert "✅ Vehicle Mil Gaya!" in message
    assert "DL01AB1234" in message
    assert "Kaam Nahi Kar Raha" in message


@pytest.mark.asyncio
async def test_validate_and_fetch_vehicle_not_found(mock_integration):
    """Test vehicle validation when vehicle is not found"""
    mock_integration.vehicle_service.get_vehicle_details = AsyncMock(return_value=None)

    is_valid, message, vehicle = await mock_integration.validate_and_fetch_vehicle("NOTFOUND")

    assert is_valid is False
    assert vehicle is None
    assert "❌ Vehicle NOTFOUND nahi mila" in message


@pytest.mark.asyncio
async def test_validate_and_fetch_vehicle_error(mock_integration):
    """Test vehicle validation when error occurs"""
    mock_integration.vehicle_service.get_vehicle_details = AsyncMock(
        side_effect=Exception("API Error")
    )

    is_valid, message, vehicle = await mock_integration.validate_and_fetch_vehicle("DL01AB1234")

    assert is_valid is False
    assert vehicle is None
    assert "problem aa rahi hai" in message


@pytest.mark.asyncio
async def test_format_vehicle_status_emoji(mock_integration):
    """Test vehicle status emoji formatting"""
    assert mock_integration._format_vehicle_status_emoji(VehicleStatus.ONLINE) == "🟢"
    assert mock_integration._format_vehicle_status_emoji(VehicleStatus.OFFLINE) == "🔴"
    assert mock_integration._format_vehicle_status_emoji(VehicleStatus.NOT_WORKING) == "⚠️"
    assert mock_integration._format_vehicle_status_emoji(VehicleStatus.UNKNOWN) == "❓"


@pytest.mark.asyncio
async def test_format_vehicle_status_hindi(mock_integration):
    """Test vehicle status Hindi text formatting"""
    assert mock_integration._format_vehicle_status_hindi(VehicleStatus.ONLINE) == "Online"
    assert mock_integration._format_vehicle_status_hindi(VehicleStatus.OFFLINE) == "Offline"
    assert mock_integration._format_vehicle_status_hindi(VehicleStatus.NOT_WORKING) == "Kaam Nahi Kar Raha"
    assert mock_integration._format_vehicle_status_hindi(VehicleStatus.UNKNOWN) == "Status Pata Nahi"


@pytest.mark.asyncio
async def test_format_vehicle_found_message_not_working(mock_integration, sample_vehicle_details):
    """Test message formatting for not working vehicle"""
    message = mock_integration._format_vehicle_found_message(sample_vehicle_details)

    assert "✅ Vehicle Mil Gaya!" in message
    assert "DL01AB1234" in message
    assert "⚠️ Status: Kaam Nahi Kar Raha" in message
    assert "📍 Last Location: Delhi NCR" in message
    assert "👤 Owner: John Doe" in message
    assert "troubleshooting start karna chahenge?" in message
    assert "1️⃣ Haan" in message
    assert "2️⃣ Nahi" in message


@pytest.mark.asyncio
async def test_format_vehicle_found_message_online(mock_integration):
    """Test message formatting for online vehicle"""
    vehicle = VehicleDetails(
        vehicle_number="DL01AB1234",
        status=VehicleStatus.ONLINE,
    )

    message = mock_integration._format_vehicle_found_message(vehicle)

    assert "✅ Vehicle Mil Gaya!" in message
    assert "🟢 Status: Online" in message
    assert "✅ Vehicle online hai aur kaam kar raha hai" in message


@pytest.mark.asyncio
async def test_format_vehicle_found_message_offline(mock_integration):
    """Test message formatting for offline vehicle"""
    vehicle = VehicleDetails(
        vehicle_number="DL01AB1234",
        status=VehicleStatus.OFFLINE,
    )

    message = mock_integration._format_vehicle_found_message(vehicle)

    assert "🔴 Status: Offline" in message
    assert "🔴 Yeh vehicle offline hai" in message


@pytest.mark.asyncio
async def test_format_vehicle_summary_for_context(mock_integration, sample_vehicle_details):
    """Test vehicle summary formatting for context"""
    summary = mock_integration.format_vehicle_summary_for_context(sample_vehicle_details)

    assert summary["vehicle_number"] == "DL01AB1234"
    assert summary["vehicle_status"] == "NOT_WORKING"
    assert summary["vehicle_imei"] == "123456789012345"
    assert summary["vehicle_owner_name"] == "John Doe"
    assert summary["vehicle_owner_phone"] == "9876543210"
    assert summary["vehicle_last_location"] == "Delhi NCR"


@pytest.mark.asyncio
async def test_get_not_working_vehicles_message_with_vehicles(mock_integration):
    """Test not working vehicles message when vehicles exist"""
    from app.schemas.vehicle_schema import VehicleSearchResponse, NotWorkingVehiclesResponse

    mock_result = NotWorkingVehiclesResponse(
        total_count=3,
        vehicles=[
            VehicleSearchResponse(
                vehicle_number="DL01AB1234",
                status=VehicleStatus.NOT_WORKING,
                owner_name="Owner 1",
            ),
            VehicleSearchResponse(
                vehicle_number="DL02CD5678",
                status=VehicleStatus.NOT_WORKING,
                owner_name="Owner 2",
            ),
            VehicleSearchResponse(
                vehicle_number="DL03EF9012",
                status=VehicleStatus.NOT_WORKING,
                owner_name="Owner 3",
            ),
        ],
    )

    mock_integration.vehicle_service.get_not_working_vehicles = AsyncMock(return_value=mock_result)

    message = await mock_integration.get_not_working_vehicles_message()

    assert "⚠️ Total 3 vehicles NOT WORKING hain" in message
    assert "DL01AB1234" in message
    assert "DL02CD5678" in message
    assert "DL03EF9012" in message


@pytest.mark.asyncio
async def test_get_not_working_vehicles_message_empty(mock_integration):
    """Test not working vehicles message when no vehicles"""
    from app.schemas.vehicle_schema import NotWorkingVehiclesResponse

    mock_result = NotWorkingVehiclesResponse(total_count=0, vehicles=[])

    mock_integration.vehicle_service.get_not_working_vehicles = AsyncMock(return_value=mock_result)

    message = await mock_integration.get_not_working_vehicles_message()

    assert "✅ Koi bhi vehicle NOT WORKING status mein nahi hai" in message
    assert "Sabhi vehicles theek kaam kar rahe hain!" in message


@pytest.mark.asyncio
async def test_get_not_working_vehicles_message_error(mock_integration):
    """Test not working vehicles message when error occurs"""
    mock_integration.vehicle_service.get_not_working_vehicles = AsyncMock(
        side_effect=Exception("API Error")
    )

    message = await mock_integration.get_not_working_vehicles_message()

    assert "problem aa rahi hai" in message
