# Vehicle API Integration - Architecture Diagrams

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                          │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                        API Layer (Routes)                       │ │
│  │                                                                  │ │
│  │  GET /vehicles/health                                           │ │
│  │  GET /vehicles/{vehicle_number}                                 │ │
│  │  GET /vehicles/{vehicle_number}/status                          │ │
│  │  GET /vehicles/{vehicle_number}/location                        │ │
│  │  GET /vehicles/search?vehicle_number=X                          │ │
│  │  GET /vehicles/not-working                                      │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                        │
│                              ▼                                        │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                      Service Layer                              │ │
│  │                                                                  │ │
│  │  ┌──────────────────────┐    ┌──────────────────────────────┐ │ │
│  │  │ VehicleAPIService    │    │ VehicleWhatsAppIntegration   │ │ │
│  │  │                      │    │                              │ │ │
│  │  │ • get_vehicle_details│    │ • validate_and_fetch_vehicle │ │ │
│  │  │ • get_vehicle_status │    │ • format_messages            │ │ │
│  │  │ • get_vehicle_location│   │ • format_context             │ │ │
│  │  │ • search_vehicle     │    │ • get_not_working_message    │ │ │
│  │  │ • get_not_working    │    │                              │ │ │
│  │  │ • health_check       │    │                              │ │ │
│  │  └──────────────────────┘    └──────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                        │
│                              ▼                                        │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                      Client Layer                               │ │
│  │                                                                  │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │              VehicleAPIClient                             │ │ │
│  │  │                                                            │ │ │
│  │  │  • Connection Pooling (100 connections)                   │ │ │
│  │  │  • Retry Logic (3 attempts, exponential backoff)          │ │ │
│  │  │  • Timeout Protection (30s default)                       │ │ │
│  │  │  • Error Handling (7 exception types)                     │ │ │
│  │  │  • Request/Response Logging                               │ │ │
│  │  │  • Health Monitoring                                      │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                        │
└──────────────────────────────┼────────────────────────────────────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │    External Vehicle API        │
              │    gtrac.in:8089               │
              │                                │
              │  • getListVehiclesmob          │
              │  • Authentication Required     │
              │  • HTTPS                       │
              └────────────────────────────────┘
```

## Data Flow Diagram

```
┌──────────┐
│  User    │
│ WhatsApp │
└────┬─────┘
     │ "DL01AB1234"
     ▼
┌────────────────────────────────────────────────────────────┐
│                    Webhook Handler                          │
│  • Receive message                                          │
│  • Extract vehicle number                                   │
│  • Route to support flow                                    │
└────┬───────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────┐
│              Support Flow Service                           │
│  • Identify conversation step                              │
│  • Call vehicle validation                                 │
└────┬───────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────┐
│         VehicleWhatsAppIntegration                          │
│  • validate_and_fetch_vehicle("DL01AB1234")                │
└────┬───────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────┐
│              VehicleAPIService                              │
│  • Check Redis cache (if enabled)                          │
│  • Call external API (if cache miss)                       │
│  • Normalize response                                      │
│  • Cache result                                            │
└────┬───────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────┐
│              VehicleAPIClient                               │
│  • Build HTTP request                                      │
│  • Add authentication                                      │
│  • Send request with retry                                 │
│  • Handle errors                                           │
│  • Return response                                         │
└────┬───────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────┐
│           External Vehicle API                              │
│  • Authenticate request                                    │
│  • Fetch vehicle data                                      │
│  • Return JSON response                                    │
└────┬───────────────────────────────────────────────────────┘
     │
     ▼ (Response flows back up)
┌────────────────────────────────────────────────────────────┐
│         VehicleWhatsAppIntegration                          │
│  • Format Hindi/English message                            │
│  • Prepare context for storage                             │
│  • Return (is_valid, message, vehicle_details)             │
└────┬───────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────┐
│              Support Flow Service                           │
│  • Store vehicle context in state                          │
│  • Update conversation step                                │
│  • Return formatted message                                │
└────┬───────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────┐
│                 Webhook Handler                             │
│  • Send message via WhatsApp                               │
│  • Save chat history                                       │
└────┬───────────────────────────────────────────────────────┘
     │
     ▼
┌──────────┐
│  User    │
│ WhatsApp │
│ Receives │
│ Message  │
└──────────┘
```

## Component Interaction

```
┌─────────────────────────────────────────────────────────────┐
│                    Component Layers                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Layer 1: API Routes (app/api/vehicles.py)                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ • FastAPI endpoints                                     │ │
│  │ • Request validation                                    │ │
│  │ • Response serialization                                │ │
│  │ • HTTP error handling                                   │ │
│  │ • Dependency injection                                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                    │
│                          ▼                                    │
│  Layer 2: Service Layer                                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ VehicleAPIService (app/services/vehicle_api_service.py)│ │
│  │ • Business logic                                        │ │
│  │ • Data normalization                                    │ │
│  │ • Caching logic                                         │ │
│  │ • Response parsing                                      │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ VehicleWhatsAppIntegration                             │ │
│  │ (app/services/vehicle_whatsapp_integration.py)         │ │
│  │ • Message formatting                                    │ │
│  │ • Context preparation                                   │ │
│  │ • User-friendly responses                               │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                    │
│                          ▼                                    │
│  Layer 3: Client Layer                                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ VehicleAPIClient (app/clients/vehicle_api_client.py)   │ │
│  │ • HTTP communication                                    │ │
│  │ • Connection pooling                                    │ │
│  │ • Retry logic                                           │ │
│  │ • Error handling                                        │ │
│  │ • Logging                                               │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                    │
│                          ▼                                    │
│  Layer 4: External API                                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Vehicle Tracking API (gtrac.in:8089)                   │ │
│  │ • Vehicle data source                                   │ │
│  │ • Authentication required                               │ │
│  │ • HTTPS endpoint                                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Caching Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Request Flow with Cache                    │
└──────────────────────────────────────────────────────────────┘

Request: GET /vehicles/DL01AB1234
    │
    ▼
┌─────────────────────────────────┐
│   VehicleAPIService             │
│   get_vehicle_details()         │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│   Check Redis Cache             │
│   Key: vehicle:details:DL01AB1234│
└─────────────────────────────────┘
    │
    ├─── Cache HIT ────────────────┐
    │                               │
    │                               ▼
    │                    ┌─────────────────────┐
    │                    │  Return cached data │
    │                    │  (Fast: ~10ms)      │
    │                    └─────────────────────┘
    │
    └─── Cache MISS ───────────────┐
                                    │
                                    ▼
                        ┌─────────────────────────┐
                        │  Call External API      │
                        │  (Slow: ~200-500ms)     │
                        └─────────────────────────┘
                                    │
                                    ▼
                        ┌─────────────────────────┐
                        │  Parse & Normalize      │
                        │  Response               │
                        └─────────────────────────┘
                                    │
                                    ▼
                        ┌─────────────────────────┐
                        │  Store in Redis         │
                        │  TTL: 5 minutes         │
                        └─────────────────────────┘
                                    │
                                    ▼
                        ┌─────────────────────────┐
                        │  Return fresh data      │
                        └─────────────────────────┘
```

## Error Handling Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    Error Handling Chain                       │
└──────────────────────────────────────────────────────────────┘

API Request
    │
    ▼
┌─────────────────────────────────┐
│   VehicleAPIClient              │
│   _make_request()               │
└─────────────────────────────────┘
    │
    ├─── Success (200) ────────────┐
    │                               │
    │                               ▼
    │                    ┌─────────────────────┐
    │                    │  Return JSON data   │
    │                    └─────────────────────┘
    │
    ├─── Auth Error (401/403) ─────┐
    │                               │
    │                               ▼
    │                    ┌─────────────────────────────┐
    │                    │  VehicleAPIAuthenticationError│
    │                    │  → HTTP 401                 │
    │                    └─────────────────────────────┘
    │
    ├─── Rate Limit (429) ─────────┐
    │                               │
    │                               ▼
    │                    ┌─────────────────────────────┐
    │                    │  VehicleAPIRateLimitError   │
    │                    │  → HTTP 429                 │
    │                    └─────────────────────────────┘
    │
    ├─── Server Error (500+) ──────┐
    │                               │
    │                               ▼
    │                    ┌─────────────────────────────┐
    │                    │  VehicleAPIServerError      │
    │                    │  → HTTP 500                 │
    │                    └─────────────────────────────┘
    │
    ├─── Timeout ──────────────────┐
    │                               │
    │                               ▼
    │                    ┌─────────────────────────────┐
    │                    │  VehicleAPITimeoutError     │
    │                    │  → Retry (3 attempts)       │
    │                    │  → HTTP 504                 │
    │                    └─────────────────────────────┘
    │
    └─── Connection Error ─────────┐
                                    │
                                    ▼
                        ┌─────────────────────────────┐
                        │  VehicleAPIConnectionError  │
                        │  → Retry (3 attempts)       │
                        │  → HTTP 503                 │
                        └─────────────────────────────┘
```

## WhatsApp Integration Flow

```
┌──────────────────────────────────────────────────────────────┐
│              WhatsApp Conversation Flow                       │
└──────────────────────────────────────────────────────────────┘

User sends: "DL01AB1234"
    │
    ▼
┌─────────────────────────────────┐
│   Webhook receives message      │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│   Get/Create User               │
│   Get Conversation State        │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│   Check current step            │
│   → VEHICLE_NUMBER              │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│   VehicleWhatsAppIntegration    │
│   validate_and_fetch_vehicle()  │
└─────────────────────────────────┘
    │
    ├─── Vehicle Found ────────────┐
    │                               │
    │                               ▼
    │                    ┌─────────────────────────────┐
    │                    │  Format success message:    │
    │                    │  ✅ Vehicle Mil Gaya!       │
    │                    │  📋 DL01AB1234              │
    │                    │  ⚠️ Status: NOT_WORKING     │
    │                    │  📍 Location: Delhi NCR     │
    │                    │  👤 Owner: John Doe         │
    │                    └─────────────────────────────┘
    │                               │
    │                               ▼
    │                    ┌─────────────────────────────┐
    │                    │  Store in context:          │
    │                    │  • vehicle_number           │
    │                    │  • vehicle_status           │
    │                    │  • vehicle_owner_name       │
    │                    │  • vehicle_location         │
    │                    └─────────────────────────────┘
    │                               │
    │                               ▼
    │                    ┌─────────────────────────────┐
    │                    │  Update conversation step   │
    │                    │  → ASK_DRIVER_AVAILABILITY  │
    │                    └─────────────────────────────┘
    │                               │
    │                               ▼
    │                    ┌─────────────────────────────┐
    │                    │  Send WhatsApp message      │
    │                    │  Save chat history          │
    │                    └─────────────────────────────┘
    │
    └─── Vehicle Not Found ────────┐
                                    │
                                    ▼
                        ┌─────────────────────────────┐
                        │  Format error message:      │
                        │  ❌ Vehicle nahi mila       │
                        │  Kripya dobara check karein │
                        └─────────────────────────────┘
                                    │
                                    ▼
                        ┌─────────────────────────────┐
                        │  Send WhatsApp message      │
                        │  Stay in VEHICLE_NUMBER step│
                        └─────────────────────────────┘
```

## Deployment Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Production Environment                     │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      Load Balancer                           │
│                      (Nginx/HAProxy)                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Application                        │
│                   (Multiple Instances)                       │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Instance 1  │  │  Instance 2  │  │  Instance 3  │      │
│  │  Port 8000   │  │  Port 8001   │  │  Port 8002   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Redis Cache                             │
│                      (Shared)                                │
│                                                               │
│  • Vehicle details cache                                     │
│  • TTL: 5 minutes                                            │
│  • High availability                                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                        │
│                   (Conversation State)                       │
│                                                               │
│  • User data                                                 │
│  • Conversation states                                       │
│  • Chat history                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  External Vehicle API                        │
│                  (gtrac.in:8089)                             │
│                                                               │
│  • Vehicle tracking data                                     │
│  • HTTPS endpoint                                            │
│  • Authentication required                                   │
└─────────────────────────────────────────────────────────────┘
```

## Monitoring & Observability

```
┌──────────────────────────────────────────────────────────────┐
│                    Monitoring Stack                           │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   Application Logs                           │
│                                                               │
│  • Request/Response logs                                     │
│  • Error logs                                                │
│  • Performance metrics                                       │
│  • Cache hit/miss ratio                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Log Aggregation                            │
│                   (ELK/Splunk/CloudWatch)                    │
│                                                               │
│  • Centralized logging                                       │
│  • Search and analysis                                       │
│  • Alerting                                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Metrics & Dashboards                       │
│                   (Grafana/Datadog)                          │
│                                                               │
│  • API response times                                        │
│  • Error rates                                               │
│  • Cache performance                                         │
│  • External API health                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Alerting System                            │
│                   (PagerDuty/Slack)                          │
│                                                               │
│  • High error rate alerts                                    │
│  • API downtime alerts                                       │
│  • Performance degradation                                   │
│  • Authentication failures                                   │
└─────────────────────────────────────────────────────────────┘
```

---

**Note**: These diagrams provide a visual representation of the Vehicle API Integration architecture. For detailed implementation, refer to the code and documentation.
