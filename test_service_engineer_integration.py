"""
Integration Test for Service Engineer Assignment Workflow
Tests the complete flow from webhook to database
"""

import asyncio
import sys
from datetime import datetime, date, time as time_type
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Add app to path
sys.path.insert(0, '.')

from app.db.database import Base
from app.db.models.ticket import Ticket
from app.db.models.conversation_state import ConversationState
from app.services.intent_classification_service import IntentClassificationService
from app.services.service_engineer_flow_service import ServiceEngineerFlowService
from app.services.ticket_service import TicketService
from app.services.state_manager import StateManager, ConversationStep
from app.repositories.ticket_repository import TicketRepository
from app.schemas.ticket_schema import IssueType

# Test database
engine = create_engine("sqlite:///ai_support.db")

async def test_gps_removed_flow():
    """Test GPS REMOVED flow with complete data collection"""
    print("\n" + "=" * 80)
    print("TEST 1: GPS REMOVED FLOW")
    print("=" * 80)
    
    db = Session(engine)
    
    try:
        # Create a test ticket
        ticket_repo = TicketRepository()
        ticket_service = TicketService(ticket_repo)
        
        ticket = await ticket_service.create_service_request_ticket(
            db=db,
            customer_phone="+919876543210",
            vehicle_number="MH12AB1234",
            issue_type=IssueType.GPS_REMOVED,
            location="Andheri, Mumbai",
            owner_name="Rajesh Kumar",
            owner_mobile="+919876543210",
            reinstallation_date=date(2026, 6, 15),
            reinstallation_time=time_type(10, 30),
            vehicle_available=True
        )
        
        print(f"✅ Ticket created: {ticket.ticket_number}")
        print(f"   Issue Type: {ticket.issue_type}")
        print(f"   Vehicle: {ticket.vehicle_number}")
        print(f"   Location: {ticket.location}")
        print(f"   Owner: {ticket.owner_name} ({ticket.owner_mobile})")
        print(f"   Reinstallation: {ticket.reinstallation_date} at {ticket.reinstallation_time}")
        print(f"   Vehicle Available: {ticket.vehicle_available}")
        print(f"   Status: {ticket.status}")
        
        # Verify data was saved correctly
        saved_ticket = ticket_repo.get_by_ticket_number(db, ticket.ticket_number)
        assert saved_ticket is not None
        assert saved_ticket.issue_type == IssueType.GPS_REMOVED.value
        assert saved_ticket.vehicle_number == "MH12AB1234"
        assert saved_ticket.location == "Andheri, Mumbai"
        
        print("\n✅ GPS REMOVED FLOW TEST PASSED")
        
        # Cleanup
        db.delete(ticket)
        db.commit()
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

async def test_vehicle_standing_flow():
    """Test VEHICLE STANDING flow with 48-hour check"""
    print("\n" + "=" * 80)
    print("TEST 2: VEHICLE STANDING FLOW (Less than 48 hours)")
    print("=" * 80)
    
    db = Session(engine)
    
    try:
        ticket_repo = TicketRepository()
        ticket_service = TicketService(ticket_repo)
        
        # Test case: Vehicle standing less than 48 hours
        ticket = await ticket_service.create_service_request_ticket(
            db=db,
            customer_phone="+919876543211",
            vehicle_number="DL01XY9876",
            issue_type=IssueType.VEHICLE_STANDING,
            location="Connaught Place, Delhi",
            standing_duration="24-48 hrs",
            inspection_date=date(2026, 6, 14),
            inspection_time=time_type(14, 0)
        )
        
        print(f"✅ Ticket created: {ticket.ticket_number}")
        print(f"   Issue Type: {ticket.issue_type}")
        print(f"   Vehicle: {ticket.vehicle_number}")
        print(f"   Standing Duration: {ticket.standing_duration}")
        print(f"   Inspection: {ticket.inspection_date} at {ticket.inspection_time}")
        print(f"   Status: {ticket.status}")
        
        # Verify
        assert ticket.standing_duration == "24-48 hrs"
        assert ticket.issue_type == IssueType.VEHICLE_STANDING.value
        
        print("\n✅ VEHICLE STANDING FLOW TEST PASSED")
        
        # Cleanup
        db.delete(ticket)
        db.commit()
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

async def test_workshop_flow():
    """Test WORKSHOP flow with auto-close"""
    print("\n" + "=" * 80)
    print("TEST 3: WORKSHOP FLOW (Auto Close)")
    print("=" * 80)
    
    db = Session(engine)
    
    try:
        ticket_repo = TicketRepository()
        ticket_service = TicketService(ticket_repo)
        
        # Create ticket
        ticket = Ticket(
            ticket_number=f"WS{datetime.now().strftime('%Y%m%d%H%M%S')}",
            customer_phone="+919876543212",
            vehicle_number="KA03CD5678",
            issue_type=IssueType.WORKSHOP.value,
            status="open"
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        
        print(f"✅ Ticket created: {ticket.ticket_number}")
        
        # Simulate closing
        await ticket_service.close_ticket(
            db=db,
            ticket_id=ticket.id,
            closure_reason="Vehicle in workshop for repair"
        )
        
        # Verify
        db.refresh(ticket)
        assert ticket.status == "closed"
        assert ticket.closure_reason == "Vehicle in workshop for repair"
        
        print(f"   Status: {ticket.status}")
        print(f"   Closure Reason: {ticket.closure_reason}")
        print("\n✅ WORKSHOP FLOW TEST PASSED")
        
        # Cleanup
        db.delete(ticket)
        db.commit()
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

async def test_intent_classification():
    """Test intent classification service"""
    print("\n" + "=" * 80)
    print("TEST 4: INTENT CLASSIFICATION")
    print("=" * 80)
    
    service = IntentClassificationService()
    
    test_cases = [
        ("Vehicle workshop mein hai", IssueType.WORKSHOP),
        ("Accident ho gaya hai", IssueType.ACCIDENT),
        ("Battery nikali hui hai", IssueType.BATTERY_DISCONNECT),
        ("GPS nikal diya", IssueType.GPS_REMOVED),
        ("GPS toot gaya", IssueType.GPS_DAMAGED),
        ("Vehicle chal rahi hai", IssueType.VEHICLE_RUNNING),
        ("Vehicle khadi hai", IssueType.VEHICLE_STANDING),
    ]
    
    passed = 0
    failed = 0
    
    for message, expected_type in test_cases:
        try:
            result = await service.classify_intent(message)
            if result == expected_type:
                print(f"✅ '{message}' -> {result.value}")
                passed += 1
            else:
                print(f"❌ '{message}' -> Expected: {expected_type.value}, Got: {result.value}")
                failed += 1
        except Exception as e:
            print(f"❌ '{message}' -> ERROR: {str(e)}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ INTENT CLASSIFICATION TEST PASSED")
    else:
        print("⚠️  INTENT CLASSIFICATION TEST PARTIALLY FAILED")

async def main():
    """Run all integration tests"""
    print("\n" + "=" * 80)
    print("SERVICE ENGINEER ASSIGNMENT - INTEGRATION TESTS")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Run tests
    await test_intent_classification()
    await test_gps_removed_flow()
    await test_vehicle_standing_flow()
    await test_workshop_flow()
    
    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
