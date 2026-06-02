# Vehicle API - Quick Reference Guide

## 🚀 Quick Start (5 Minutes)

### 1. Install Dependencies
```bash
pip install httpx tenacity redis
```

### 2. Configure Environment
```bash
# Add to .env
VEHICLE_API_USERNAME=your_username
VEHICLE_API_PASSWORD=your_password
```

### 3. Test
```bash
# Start server
uvicorn app.main:app --reload

# Test health
curl http://localhost:8000/vehicles/health
```

## 📋 Common Tasks

### Get Vehicle Details
```python
from app.services.vehicle_api_service import VehicleAPIService

service = VehicleAPIService()
vehicle = await service.get_vehicle_details("DL01AB1234")
await service.close()
```

### Validate Vehicle in WhatsApp Flow
```python
from app.services.vehicle_whatsapp_integration import VehicleWhatsAppIntegration

integration = VehicleWhatsAppIntegration()
is_valid, message, vehicle = await integration.validate_and_fetch_vehicle("DL01AB1234")

if is_valid:
    # Store in context
    context = integration.format_vehicle_summary_for_context(vehicle)
    state_manager.update_context(phone_number, context)
    
    # Send message
    send_whatsapp_message(phone_number, message)

await integration.close()
```

### Get Not Working Vehicles
```python
service = VehicleAPIService()
result = await service.get_not_working_vehicles()
print(f"Total: {result.total_count}")
for vehicle in result.vehicles:
    print(f"{vehicle.vehicle_number} - {vehicle.owner_name}")
await service.close()
```

## 🔌 API Endpoints

```bash
# Health Check
GET /vehicles/health

# Vehicle Details
GET /vehicles/DL01AB1234

# Vehicle Status
GET /vehicles/DL01AB1234/status

# Vehicle Location
GET /vehicles/DL01AB1234/location

# Search
GET /vehicles/search?vehicle_number=DL01AB1234

# Not Working List
GET /vehicles/not-working
```

## 🎯 Status Values

```python
VehicleStatus.ONLINE       # 🟢 Vehicle is working
VehicleStatus.OFFLINE      # 🔴 Vehicle is offline
VehicleStatus.NOT_WORKING  # ⚠️ Vehicle has issues
VehicleStatus.UNKNOWN      # ❓ Status unclear
```

## 🔧 Configuration

### Minimal (Required)
```bash
VEHICLE_API_USERNAME=your_username
VEHICLE_API_PASSWORD=your_password
```

### Full (Recommended)
```bash
VEHICLE_API_BASE_URL=https://gtrac.in:8089/trackingdashboard
VEHICLE_API_USERNAME=your_username
VEHICLE_API_PASSWORD=your_password
VEHICLE_API_TIMEOUT=30
VEHICLE_API_MAX_RETRIES=3

# Optional: Enable caching
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
VEHICLE_CACHE_TTL=300
```

## 🧪 Testing

```bash
# Run all tests
pytest app/tests/test_vehicle_*.py -v

# Run specific test
pytest app/tests/test_vehicle_api_client.py -v

# With coverage
pytest app/tests/test_vehicle_*.py --cov=app --cov-report=html
```

## 🐛 Debugging

### Check Health
```bash
curl http://localhost:8000/vehicles/health
```

### Check Logs
```bash
# Look for vehicle API logs
grep "VehicleAPI" app.log

# Check errors
grep "ERROR" app.log | grep "vehicle"
```

### Test External API
```python
from app.clients.vehicle_api_client import VehicleAPIClient

client = VehicleAPIClient()
is_healthy, response_time = await client.health_check()
print(f"Healthy: {is_healthy}, Time: {response_time}ms")
await client.close()
```

## ⚠️ Common Errors

### Authentication Failed (401)
```bash
# Check credentials
echo $VEHICLE_API_USERNAME
echo $VEHICLE_API_PASSWORD

# Test with curl
curl -u username:password https://gtrac.in:8089/trackingdashboard/getListVehiclesmob
```

### Timeout (504)
```bash
# Increase timeout
VEHICLE_API_TIMEOUT=60

# Check network
ping gtrac.in
```

### Vehicle Not Found (404)
```python
# Verify vehicle number format
vehicle_number = "DL01AB1234"  # Correct
vehicle_number = "dl01ab1234"  # Also works (normalized)
vehicle_number = "DL 01 AB 1234"  # Also works (spaces removed)
```

### Redis Connection Error
```bash
# Check Redis
redis-cli ping

# Disable Redis if not needed
REDIS_ENABLED=false
```

## 📊 Response Examples

### Vehicle Details
```json
{
  "vehicle_number": "DL01AB1234",
  "imei": "123456789012345",
  "status": "NOT_WORKING",
  "last_location": {
    "latitude": 28.6139,
    "longitude": 77.2090,
    "address": "Delhi NCR"
  },
  "last_update_time": "2024-01-15T10:30:00",
  "owner_name": "John Doe",
  "owner_phone": "9876543210"
}
```

### Health Check
```json
{
  "status": "healthy",
  "external_api_reachable": true,
  "response_time_ms": 245.67,
  "cache_enabled": true,
  "cache_healthy": true
}
```

### Not Working Vehicles
```json
{
  "total_count": 3,
  "vehicles": [
    {
      "vehicle_number": "DL01AB1234",
      "status": "NOT_WORKING",
      "owner_name": "John Doe"
    }
  ]
}
```

## 🔄 WhatsApp Messages

### Vehicle Found (Not Working)
```
✅ Vehicle Mil Gaya!
📋 Vehicle Number: DL01AB1234
⚠️ Status: Kaam Nahi Kar Raha
📍 Last Location: Delhi NCR
👤 Owner: John Doe

⚠️ Yeh vehicle kaam nahi kar raha hai.

Kya aap troubleshooting start karna chahenge?
1️⃣ Haan
2️⃣ Nahi
```

### Vehicle Not Found
```
❌ Vehicle DL01AB1234 nahi mila.

Kripya vehicle number dobara check karein aur phir se bhejein.
```

### API Error
```
⚠️ Vehicle ki jaankari lene mein problem aa rahi hai.

Kripya thodi der baad dobara try karein.
```

## 💡 Best Practices

### 1. Always Close Connections
```python
service = VehicleAPIService()
try:
    vehicle = await service.get_vehicle_details("DL01AB1234")
finally:
    await service.close()
```

### 2. Use Context Manager (Future)
```python
async with VehicleAPIService() as service:
    vehicle = await service.get_vehicle_details("DL01AB1234")
```

### 3. Handle Errors Gracefully
```python
try:
    vehicle = await service.get_vehicle_details("DL01AB1234")
except VehicleAPIException as e:
    logger.error(f"Vehicle API error: {e}")
    return "Error message for user"
```

### 4. Enable Caching in Production
```bash
REDIS_ENABLED=true
VEHICLE_CACHE_TTL=300  # 5 minutes
```

### 5. Monitor Health
```python
# Regular health checks
health = await service.health_check()
if health.status != "healthy":
    alert_team()
```

## 📈 Performance Tips

1. **Enable Redis** - 5x faster responses
2. **Reuse connections** - Don't create new service for each request
3. **Adjust timeouts** - Based on your network
4. **Monitor cache hit rate** - Optimize TTL
5. **Use async/await** - Non-blocking operations

## 🔐 Security Checklist

- [ ] Credentials in environment variables
- [ ] `.env` in `.gitignore`
- [ ] HTTPS for API calls
- [ ] Regular credential rotation
- [ ] Monitor auth failures
- [ ] No secrets in logs

## 📞 Quick Help

### Issue: Can't connect to external API
```bash
# Check network
curl https://gtrac.in:8089/trackingdashboard/getListVehiclesmob

# Check credentials
echo $VEHICLE_API_USERNAME
```

### Issue: Slow responses
```bash
# Enable caching
REDIS_ENABLED=true

# Check external API
curl -w "@curl-format.txt" https://gtrac.in:8089/...
```

### Issue: Tests failing
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run with verbose output
pytest app/tests/test_vehicle_*.py -v -s
```

## 📚 Documentation Links

- **Full Documentation**: `docs/VEHICLE_API_INTEGRATION.md`
- **Integration Guide**: `docs/VEHICLE_WHATSAPP_FLOW.md`
- **Deployment**: `docs/DEPLOYMENT_CHECKLIST.md`
- **Summary**: `VEHICLE_API_SUMMARY.md`

## 🎯 Cheat Sheet

```bash
# Install
pip install -r requirements.txt

# Configure
nano .env  # Add credentials

# Test
pytest app/tests/test_vehicle_*.py -v

# Run
uvicorn app.main:app --reload

# Health Check
curl http://localhost:8000/vehicles/health

# Get Vehicle
curl http://localhost:8000/vehicles/DL01AB1234

# Logs
tail -f app.log | grep VehicleAPI
```

## 🚨 Emergency Contacts

**External API Issues:**
- Provider: gtrac.in
- Support: [Contact Info]

**Internal Issues:**
- Tech Lead: [Name]
- On-Call: [Phone]

## ✅ Pre-Deployment Checklist

- [ ] Environment variables set
- [ ] Tests passing
- [ ] Health check working
- [ ] Documentation reviewed
- [ ] Team trained
- [ ] Monitoring configured
- [ ] Rollback plan ready

---

**Last Updated**: June 1, 2026
**Version**: 1.0.0
