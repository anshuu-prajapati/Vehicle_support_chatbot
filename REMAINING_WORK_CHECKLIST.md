# Service Engineer Assignment - Remaining Work Checklist

**Last Updated**: June 13, 2026  
**Current Phase**: Testing & API Development  
**Overall Completion**: 85%

---

## ✅ COMPLETED WORK

### Phase 1: Database & Core Services (100%)
- [x] Create Alembic migration 0005
- [x] Extend Ticket model with 19 new fields
- [x] Update Ticket schema with IssueType enum
- [x] Extend StateManager with 39 new states
- [x] Create TicketRepository
- [x] Extend TicketService
- [x] Create IntentClassificationService
- [x] Create FlowRouter
- [x] Update webhook integration
- [x] Fix migration revision chain

### Phase 2: Flow Handlers (100%)
- [x] WorkshopFlowHandler
- [x] AccidentFlowHandler
- [x] BatteryFlowHandler
- [x] GpsRemovedFlowHandler
- [x] GpsDamagedFlowHandler
- [x] VehicleRunningFlowHandler
- [x] VehicleStandingFlowHandler (48-hour rule)
- [x] UnknownFlowHandler
- [x] ServiceEngineerFlowService (main orchestrator)

### Phase 3: Database Migration (100%)
- [x] Run migration 0005
- [x] Verify all 19 columns present
- [x] Create 3 database indexes
- [x] Mark database as version 0005
- [x] Create verification script
- [x] Create migration documentation

---

## 📋 PENDING WORK

### Phase 4: Integration Testing (HIGH PRIORITY)

#### 4.1 Database Tests
- [ ] Test ticket creation with all new fields
- [ ] Test ticket updates (assign engineer, close, etc.)
- [ ] Test querying by issue_type
- [ ] Test querying by vehicle_number
- [ ] Test querying by status
- [ ] Test date/time field storage and retrieval
- [ ] Verify foreign key relationship (assigned_engineer_id)

**Estimated Time**: 1-2 hours

#### 4.2 Run Integration Test Suite
- [ ] Execute `test_service_engineer_integration.py`
- [ ] Fix any failing tests
- [ ] Verify intent classification accuracy
- [ ] Verify GPS removed flow
- [ ] Verify vehicle standing flow
- [ ] Verify workshop flow with auto-close
- [ ] Document test results

**Estimated Time**: 1 hour

#### 4.3 WhatsApp Flow Testing
Manual testing required for each issue type:

- [ ] **WORKSHOP Flow**
  - Send: "Vehicle workshop mein hai"
  - Verify: Asks confirmation
  - Reply: "Haan" → Should close ticket
  - Reply: "Nahi" → Should route to manual review

- [ ] **ACCIDENT Flow**
  - Send: "Accident ho gaya"
  - Verify: Asks confirmation
  - Test both YES and NO paths

- [ ] **BATTERY Flow**
  - Send: "Battery nikali hui hai"
  - Verify: Asks confirmation
  - Test both YES and NO paths

- [ ] **GPS_REMOVED Flow**
  - Send: "GPS nikal gaya"
  - Verify: Asks for reinstallation date
  - Provide: "15/06/2026"
  - Verify: Asks for time
  - Provide: "10:30 AM"
  - Verify: Asks for location
  - Provide: "Andheri, Mumbai"
  - Verify: Asks for contact
  - Provide: "+919876543210"
  - Verify: Asks if vehicle available
  - Test both YES and NO paths

- [ ] **GPS_DAMAGED Flow**
  - Send: "GPS toot gaya"
  - Verify: Collects location, contact, inspection date/time
  - Confirm: Service request created

- [ ] **VEHICLE_RUNNING Flow**
  - Send: "Vehicle chal rahi hai"
  - Verify: Collects driver info, location, inspection date/time
  - Confirm: Service request created

- [ ] **VEHICLE_STANDING Flow**
  - Send: "Vehicle khadi hai"
  - Verify: Asks duration
  - Test: ">48 hours" → Auto-close
  - Test: "<48 hours" → Collect data and create service request

- [ ] **UNKNOWN Flow**
  - Send: "Kuch samajh nahi aa raha"
  - Verify: Asks for more details
  - Test: Reclassification logic

**Estimated Time**: 3-4 hours

#### 4.4 Bilingual Testing
- [ ] Test all flows in Hindi
- [ ] Test all flows in English
- [ ] Test mixed Hindi-English messages
- [ ] Verify date parsing in both languages
- [ ] Verify time parsing in both formats (24hr, 12hr AM/PM)

**Estimated Time**: 1-2 hours

#### 4.5 Edge Case Testing
- [ ] Invalid date formats
- [ ] Invalid time formats
- [ ] Invalid phone numbers
- [ ] Very long messages
- [ ] Special characters in messages
- [ ] Empty messages
- [ ] Conversation interruption and resume
- [ ] Multiple users simultaneously

**Estimated Time**: 2 hours

**Phase 4 Total Estimated Time**: 8-11 hours

---

### Phase 5: API Endpoints (MEDIUM PRIORITY)

#### 5.1 Ticket Management APIs
Create in `app/api/tickets.py`:

- [ ] `POST /api/tickets/{id}/assign`
  - Request: `{"engineer_id": 123}`
  - Response: Updated ticket with assigned engineer
  - Validation: Engineer exists and is available

- [ ] `POST /api/tickets/{id}/close`
  - Request: `{"closure_reason": "Issue resolved"}`
  - Response: Closed ticket
  - Validation: Ticket exists and is open

- [ ] `PATCH /api/tickets/{id}`
  - Request: Any ticket field updates
  - Response: Updated ticket
  - Validation: Field types and constraints

- [ ] `GET /api/tickets?issue_type=GPS_REMOVED`
  - Response: Filtered list of tickets
  - Support: Multiple filters (issue_type, status, vehicle_number)

- [ ] `GET /api/tickets/{id}/history`
  - Response: All state changes for ticket
  - Shows: Who changed what and when

**Estimated Time**: 3-4 hours

#### 5.2 Vehicle Monitoring APIs
Create in `app/api/vehicles.py`:

- [ ] `GET /api/vehicles/inactive`
  - Response: Vehicles inactive >48 hours
  - Include: Last location, last activity time
  - Support: Pagination

- [ ] `GET /api/vehicles/{vehicle_number}/status`
  - Response: Current vehicle status
  - Include: Location, power state, speed

- [ ] `GET /api/vehicles/{vehicle_number}/tickets`
  - Response: All tickets for vehicle
  - Support: Filter by status

**Estimated Time**: 2-3 hours

#### 5.3 Engineer Management APIs
Create in `app/api/engineers.py`:

- [ ] `GET /api/engineers/available`
  - Response: List of available engineers
  - Include: Current location, workload

- [ ] `GET /api/engineers/{id}/assignments`
  - Response: All tickets assigned to engineer
  - Support: Filter by status, date range

- [ ] `POST /api/engineers/{id}/location`
  - Request: `{"latitude": 19.1234, "longitude": 72.5678}`
  - Response: Updated engineer location

**Estimated Time**: 2-3 hours

#### 5.4 API Documentation
- [ ] Create OpenAPI/Swagger documentation
- [ ] Add request/response examples
- [ ] Document error codes and messages
- [ ] Add authentication requirements
- [ ] Create Postman collection

**Estimated Time**: 1-2 hours

**Phase 5 Total Estimated Time**: 8-12 hours

---

### Phase 6: Engineer Assignment Algorithm (MEDIUM PRIORITY)

#### 6.1 Data Model
- [ ] Create Engineer model (if not exists)
  - Fields: id, name, phone, current_location, is_available, workload
- [ ] Create migration for engineers table
- [ ] Add relationship between Ticket and Engineer

**Estimated Time**: 1-2 hours

#### 6.2 Assignment Logic
Create in `app/services/engineer_assignment_service.py`:

- [ ] Implement `find_available_engineers()`
  - Query engineers where is_available = True
  - Exclude engineers over workload limit

- [ ] Implement `calculate_proximity(engineer_location, vehicle_location)`
  - Use haversine formula for distance
  - Return distance in kilometers

- [ ] Implement `assign_nearest_engineer(ticket_id, vehicle_location)`
  - Find available engineers
  - Calculate distance for each
  - Sort by distance
  - Assign nearest
  - Update engineer workload
  - Send notifications

- [ ] Implement `notify_engineer(engineer_id, ticket_id)`
  - Send WhatsApp notification
  - Include: Vehicle number, location, issue type

- [ ] Implement `notify_customer(customer_phone, engineer_name, engineer_phone, eta)`
  - Send confirmation message
  - Include engineer details and ETA

**Estimated Time**: 4-6 hours

#### 6.3 Testing
- [ ] Unit tests for proximity calculation
- [ ] Unit tests for assignment logic
- [ ] Integration test for full assignment flow
- [ ] Test with multiple engineers
- [ ] Test when no engineers available
- [ ] Test workload balancing

**Estimated Time**: 2-3 hours

**Phase 6 Total Estimated Time**: 7-11 hours

---

### Phase 7: Unit Tests (MEDIUM PRIORITY)

#### 7.1 Flow Handler Tests
Create test files for each handler:

- [ ] `test_workshop_flow.py`
- [ ] `test_accident_flow.py`
- [ ] `test_battery_flow.py`
- [ ] `test_gps_removed_flow.py`
- [ ] `test_gps_damaged_flow.py`
- [ ] `test_vehicle_running_flow.py`
- [ ] `test_vehicle_standing_flow.py`
- [ ] `test_unknown_flow.py`

Each test should cover:
- [ ] State transitions
- [ ] Data validation
- [ ] Error handling
- [ ] Edge cases

**Estimated Time**: 4-6 hours

#### 7.2 Service Tests
- [ ] Test IntentClassificationService
  - All 8 issue types
  - Bilingual support
  - Edge cases

- [ ] Test TicketService
  - Create, read, update, delete
  - Assign engineer
  - Close ticket

- [ ] Test ServiceEngineerFlowService
  - Flow routing
  - State management
  - Error recovery

**Estimated Time**: 2-3 hours

**Phase 7 Total Estimated Time**: 6-9 hours

---

### Phase 8: Dashboard/UI (LOW PRIORITY)

#### 8.1 Backend APIs (if not already created)
- [ ] Statistics API: GET /api/dashboard/stats
- [ ] Recent tickets API: GET /api/dashboard/recent-tickets
- [ ] Engineer status API: GET /api/dashboard/engineers

**Estimated Time**: 2 hours

#### 8.2 Frontend (if applicable)
- [ ] Create ticket list view
- [ ] Create ticket detail view
- [ ] Create engineer assignment UI
- [ ] Create statistics dashboard
- [ ] Add real-time updates (WebSocket)

**Estimated Time**: 16-24 hours (full dashboard)

**Phase 8 Total Estimated Time**: 18-26 hours

---

### Phase 9: Documentation (LOW PRIORITY)

- [ ] API documentation (Swagger/OpenAPI)
- [ ] User guide for customer service team
- [ ] Engineer mobile app guide (if applicable)
- [ ] System architecture diagram
- [ ] Database schema diagram
- [ ] Deployment guide
- [ ] Troubleshooting guide
- [ ] FAQ

**Estimated Time**: 4-6 hours

---

### Phase 10: Production Deployment (FINAL)

#### 10.1 Pre-Deployment
- [ ] Backup production database
- [ ] Review all code changes
- [ ] Run full test suite
- [ ] Performance testing
- [ ] Security audit
- [ ] Create rollback plan

**Estimated Time**: 2-3 hours

#### 10.2 Deployment
- [ ] Deploy code to production
- [ ] Run migrations
- [ ] Verify migrations successful
- [ ] Smoke test critical flows
- [ ] Monitor error logs
- [ ] Monitor performance metrics

**Estimated Time**: 1-2 hours

#### 10.3 Post-Deployment
- [ ] Monitor for 24 hours
- [ ] Collect user feedback
- [ ] Fix any critical issues
- [ ] Document lessons learned
- [ ] Create post-deployment report

**Estimated Time**: 2-4 hours

**Phase 10 Total Estimated Time**: 5-9 hours

---

## 📊 ESTIMATED TIME SUMMARY

| Phase | Priority | Time Estimate |
|-------|----------|---------------|
| Phase 4: Testing | HIGH | 8-11 hours |
| Phase 5: API Endpoints | MEDIUM | 8-12 hours |
| Phase 6: Engineer Assignment | MEDIUM | 7-11 hours |
| Phase 7: Unit Tests | MEDIUM | 6-9 hours |
| Phase 8: Dashboard | LOW | 18-26 hours |
| Phase 9: Documentation | LOW | 4-6 hours |
| Phase 10: Deployment | FINAL | 5-9 hours |

**Total Remaining Work**: 56-84 hours (7-10 business days)

---

## 🎯 RECOMMENDED NEXT STEPS

### This Week (Priority 1)
1. Run integration tests (1 hour)
2. Manual WhatsApp testing (3-4 hours)
3. Create core API endpoints (4 hours)

**Total**: 8-9 hours

### Next Week (Priority 2)
1. Implement engineer assignment (7-11 hours)
2. Add unit tests (6-9 hours)
3. Complete API documentation (2 hours)

**Total**: 15-22 hours

### Following Week (Priority 3)
1. Build dashboard (optional)
2. Complete documentation
3. Deploy to production

---

## 🚦 BLOCKING ISSUES

None currently. All dependencies are resolved.

---

## 📝 NOTES

- Engineer assignment algorithm is the most complex remaining task
- WhatsApp testing must be done manually (cannot be automated)
- Dashboard is optional - API endpoints are sufficient for MVP
- Production deployment should be done during low-traffic hours

---

## ✅ SUCCESS METRICS

System is production-ready when:
- [ ] All integration tests pass
- [ ] All 8 WhatsApp flows tested manually
- [ ] Core API endpoints functional
- [ ] Engineer assignment working
- [ ] No critical bugs
- [ ] Performance acceptable (< 2s response time)
- [ ] Documentation complete

**Current Progress**: 85% complete
**Estimated Completion**: 7-10 business days
