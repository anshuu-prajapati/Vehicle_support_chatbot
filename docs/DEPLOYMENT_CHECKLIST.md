# Vehicle API Integration - Deployment Checklist

## Pre-Deployment

### 1. Environment Configuration

- [ ] Copy `.env.example` to `.env` (if not exists)
- [ ] Set `VEHICLE_API_BASE_URL` (default: https://gtrac.in:8089/trackingdashboard)
- [ ] Set `VEHICLE_API_USERNAME` (required)
- [ ] Set `VEHICLE_API_PASSWORD` (required)
- [ ] Set `VEHICLE_API_TIMEOUT` (default: 30)
- [ ] Set `VEHICLE_API_MAX_RETRIES` (default: 3)
- [ ] Configure Redis (optional):
  - [ ] Set `REDIS_ENABLED=true`
  - [ ] Set `REDIS_HOST`
  - [ ] Set `REDIS_PORT`
  - [ ] Set `REDIS_PASSWORD` (if required)
  - [ ] Set `VEHICLE_CACHE_TTL` (default: 300)

### 2. Dependencies Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Or using virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Verify Installation

```bash
# Check httpx
python -c "import httpx; print(httpx.__version__)"

# Check tenacity
python -c "import tenacity; print(tenacity.__version__)"

# Check redis (if enabled)
python -c "import redis; print(redis.__version__)"
```

## Testing

### 1. Unit Tests

```bash
# Run all vehicle tests
pytest app/tests/test_vehicle_*.py -v

# Run with coverage
pytest app/tests/test_vehicle_*.py --cov=app.clients --cov=app.services --cov-report=html

# Expected: All tests pass
```

### 2. Integration Tests

```bash
# Start the application
uvicorn app.main:app --reload

# Test health endpoint
curl http://localhost:8000/vehicles/health

# Expected response:
# {
#   "status": "healthy",
#   "external_api_reachable": true,
#   "response_time_ms": 245.67,
#   "cache_enabled": false,
#   "cache_healthy": false
# }
```

### 3. API Endpoint Tests

```bash
# Test vehicle details
curl http://localhost:8000/vehicles/DL01AB1234

# Test vehicle status
curl http://localhost:8000/vehicles/DL01AB1234/status

# Test vehicle location
curl http://localhost:8000/vehicles/DL01AB1234/location

# Test not working vehicles
curl http://localhost:8000/vehicles/not-working

# Test search
curl "http://localhost:8000/vehicles/search?vehicle_number=DL01AB1234"
```

### 4. WhatsApp Flow Test

- [ ] Send vehicle number via WhatsApp
- [ ] Verify vehicle details are returned
- [ ] Check conversation context is updated
- [ ] Verify flow continues correctly
- [ ] Test invalid vehicle number
- [ ] Test API timeout scenario

## Deployment

### 1. Code Deployment

```bash
# Pull latest code
git pull origin main

# Install/update dependencies
pip install -r requirements.txt

# Restart application
# (Method depends on your deployment setup)
```

### 2. Database Migrations

```bash
# No database changes required for this feature
# Existing conversation_states table is used for context storage
```

### 3. Application Restart

```bash
# Using systemd
sudo systemctl restart fastapi-app

# Using supervisor
sudo supervisorctl restart fastapi-app

# Using PM2
pm2 restart fastapi-app

# Using Docker
docker-compose restart app
```

## Post-Deployment Verification

### 1. Health Check

```bash
# Check application health
curl http://your-domain.com/vehicles/health

# Expected: status = "healthy"
```

### 2. Smoke Tests

```bash
# Test a known vehicle
curl http://your-domain.com/vehicles/KNOWN_VEHICLE_NUMBER

# Test not working vehicles
curl http://your-domain.com/vehicles/not-working

# Expected: Valid responses with data
```

### 3. Log Verification

```bash
# Check application logs
tail -f /var/log/fastapi-app/app.log

# Look for:
# - "VehicleAPIClient initialized"
# - "VehicleAPIService initialized"
# - Successful API requests
# - No authentication errors
```

### 4. WhatsApp Integration Test

- [ ] Send test vehicle number via WhatsApp
- [ ] Verify response is received
- [ ] Check vehicle details are correct
- [ ] Verify conversation continues
- [ ] Test menu option "Check Vehicle Status"
- [ ] Test menu option "Not Working Vehicles List"

## Monitoring Setup

### 1. Application Metrics

```bash
# Monitor API response times
# Monitor error rates
# Monitor cache hit/miss ratio (if Redis enabled)
# Monitor connection pool usage
```

### 2. Alerts Configuration

- [ ] Set up alert for authentication failures
- [ ] Set up alert for high error rate (>5%)
- [ ] Set up alert for slow response times (>5s)
- [ ] Set up alert for API downtime

### 3. Log Aggregation

- [ ] Configure log shipping to centralized system
- [ ] Set up log parsing for vehicle API events
- [ ] Create dashboards for key metrics

## Performance Optimization

### 1. Enable Redis Caching

```bash
# Install Redis
sudo apt-get install redis-server

# Start Redis
sudo systemctl start redis

# Enable in .env
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 2. Connection Pool Tuning

```python
# In vehicle_api_client.py
# Adjust based on your load:
limits = httpx.Limits(
    max_keepalive_connections=20,  # Increase for high load
    max_connections=100,            # Increase for high load
    keepalive_expiry=30.0,
)
```

### 3. Timeout Configuration

```bash
# Adjust based on network conditions
VEHICLE_API_TIMEOUT=30  # Increase if network is slow
VEHICLE_API_MAX_RETRIES=3  # Increase for unreliable networks
```

## Rollback Plan

### If Issues Occur

1. **Disable Vehicle API Integration**
   ```bash
   # Add to .env
   USE_VEHICLE_API=false
   
   # Restart application
   sudo systemctl restart fastapi-app
   ```

2. **Revert Code Changes**
   ```bash
   git revert HEAD
   git push origin main
   # Redeploy
   ```

3. **Check Logs for Root Cause**
   ```bash
   grep "VehicleAPI" /var/log/fastapi-app/app.log
   grep "ERROR" /var/log/fastapi-app/app.log
   ```

## Security Checklist

- [ ] Credentials are stored in environment variables
- [ ] `.env` file is in `.gitignore`
- [ ] API credentials are rotated regularly
- [ ] HTTPS is used for all API communication
- [ ] Rate limiting is configured
- [ ] Authentication failures are monitored
- [ ] Sensitive data is not logged

## Documentation

- [ ] API documentation is updated
- [ ] Team is trained on new features
- [ ] Runbook is created for common issues
- [ ] Architecture diagram is updated
- [ ] Monitoring dashboard is shared

## Success Criteria

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Health check returns "healthy"
- [ ] Vehicle details are fetched successfully
- [ ] WhatsApp flow works end-to-end
- [ ] No authentication errors in logs
- [ ] Response times are acceptable (<1s)
- [ ] Error rate is low (<1%)
- [ ] Cache is working (if enabled)
- [ ] Monitoring is active

## Common Issues & Solutions

### Issue 1: Authentication Failed

**Symptoms:**
```
VehicleAPIAuthenticationError: Authentication failed with status 401
```

**Solution:**
1. Verify `VEHICLE_API_USERNAME` and `VEHICLE_API_PASSWORD`
2. Check if credentials are correct
3. Test credentials with external API directly
4. Rotate credentials if compromised

### Issue 2: Connection Timeout

**Symptoms:**
```
VehicleAPITimeoutError: Request timeout after 30s
```

**Solution:**
1. Check network connectivity
2. Increase `VEHICLE_API_TIMEOUT`
3. Check if external API is down
4. Verify firewall rules

### Issue 3: Vehicle Not Found

**Symptoms:**
```
HTTPException(404): Vehicle DL01AB1234 not found
```

**Solution:**
1. Verify vehicle number format
2. Check if vehicle exists in external system
3. Test with known vehicle number
4. Check API response format

### Issue 4: Redis Connection Error

**Symptoms:**
```
Warning: Cache read/write error
```

**Solution:**
1. Check if Redis is running: `sudo systemctl status redis`
2. Verify Redis connection settings
3. Test Redis connection: `redis-cli ping`
4. Application continues without cache (graceful degradation)

### Issue 5: High Response Times

**Symptoms:**
- Response times >5 seconds
- Slow WhatsApp responses

**Solution:**
1. Enable Redis caching
2. Increase connection pool size
3. Check external API performance
4. Monitor network latency

## Maintenance

### Daily

- [ ] Check error logs
- [ ] Monitor response times
- [ ] Verify health check status

### Weekly

- [ ] Review cache hit/miss ratio
- [ ] Analyze most checked vehicles
- [ ] Check for authentication issues
- [ ] Review error patterns

### Monthly

- [ ] Rotate API credentials
- [ ] Review and optimize cache TTL
- [ ] Analyze performance trends
- [ ] Update documentation

## Contact Information

**Technical Support:**
- Email: tech-support@company.com
- Slack: #vehicle-api-support

**On-Call:**
- Primary: [Name] - [Phone]
- Secondary: [Name] - [Phone]

**External API Support:**
- Provider: gtrac.in
- Support: [Contact Info]

## Sign-off

- [ ] Development Team Lead: _________________ Date: _______
- [ ] QA Team Lead: _________________ Date: _______
- [ ] DevOps Lead: _________________ Date: _______
- [ ] Product Owner: _________________ Date: _______

## Notes

_Add any deployment-specific notes here_

---

**Deployment Date:** _________________

**Deployed By:** _________________

**Version:** _________________

**Status:** ☐ Success ☐ Partial ☐ Rollback
