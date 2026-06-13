#!/usr/bin/env python3
"""
Test script for GPS Re-check functionality.

This test verifies that the GPS_REPAIR_RECHECK handler works correctly for:
1. User selects "1" (check again) - triggers new GPS verification
2. User selects "2" (talk later) - ends conversation 
3. Invalid responses - shows options again

Tests both successful and failed GPS re-verification scenarios.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from unittest.mock import Mock, patch, MagicMock
from app.services.support_flow_service import handle_support_message
from app.services.state_manager import StateManager, ConversationStep
from app.db.models.user import User

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_gps_recheck_check_again():
    """Test GPS recheck when user selects '1' (check again)."""
    print("\n" + "="*60)
    print("TEST: GPS Recheck - User selects '1' (Check Again)")
    print("="*60)
    
    # Mock dependencies
    mock_db = Mock()
    mock_state_manager = Mock(spec=StateManager)
    mock_user = Mock(spec=User)
    mock_user.phone_number = "+919876543210"
    mock_user.name = "Test Driver"
    
    # Set up state to be GPS_REPAIR_RECHECK
    mock_state = Mock()
    mock_state.current_step = ConversationStep.GPS_REPAIR_RECHECK.value
    mock_state_manager.get_state.return_value = mock_state
    mock_state_manager.get_context.return_value = {
        "vehicle_number": "MH12AB1234",
        "baseline_latitude": 19.0760,
        "baseline_longitude": 72.8777,
        "baseline_gps_time": "2024-01-15T10:00:00Z"
    }
    
    # Mock successful GPS verification result
    with patch('app.services.support_flow_service._perform_gps_verification') as mock_gps_verify:
        mock_gps_verify.return_value = (
            "🎉 परफेक्ट! GPS सफलतापूर्वक अपडेट हो रहा है।\n"
            "🎉 Perfect! GPS is successfully updating.\n\n"
            "📍 पुराना स्थान: 19.076000, 72.877700\n"
            "📍 Old location: 19.076000, 72.877700\n\n"
            "📍 नया स्थान: 19.076500, 72.878200\n"
            "📍 New location: 19.076500, 72.878200\n\n"
            "निर्देशांक बदलने से पता चलता है कि GPS सिस्टम बिल्कुल सही तरीके से काम कर रहा है! ✅\n"
            "The coordinate change confirms that the GPS system is working perfectly! ✅\n\n"
            "धन्यवाद! / Thank you!"
        )
        
        # Test user input "1" for check again
        response = handle_support_message(
            user=mock_user,
            text_body="1",
            state_manager=mock_state_manager,
            db=mock_db
        )
        
        print(f"User Input: '1' (Check again)")
        print(f"Response: {response}")
        
        # Verify GPS verification was called
        mock_gps_verify.assert_called_once_with(mock_user.phone_number, mock_db, mock_state_manager)
        
        # Verify state was set to GPS_REPAIR_VERIFICATION
        mock_state_manager.set_state.assert_called_with(
            mock_user.phone_number, 
            ConversationStep.GPS_REPAIR_VERIFICATION
        )
        
        print("✅ GPS re-verification triggered successfully")
        print("✅ State properly transitioned to GPS_REPAIR_VERIFICATION")
        
    return True

def test_gps_recheck_talk_later():
    """Test GPS recheck when user selects '2' (talk later)."""
    print("\n" + "="*60)
    print("TEST: GPS Recheck - User selects '2' (Talk Later)")
    print("="*60)
    
    # Mock dependencies
    mock_db = Mock()
    mock_state_manager = Mock(spec=StateManager)
    mock_user = Mock(spec=User)
    mock_user.phone_number = "+919876543210"
    mock_user.name = "Test Driver"
    
    # Set up state to be GPS_REPAIR_RECHECK
    mock_state = Mock()
    mock_state.current_step = ConversationStep.GPS_REPAIR_RECHECK.value
    mock_state_manager.get_state.return_value = mock_state
    mock_state_manager.get_context.return_value = {
        "vehicle_number": "MH12AB1234"
    }
    
    # Test user input "2" for talk later
    response = handle_support_message(
        user=mock_user,
        text_body="2",
        state_manager=mock_state_manager,
        db=mock_db
    )
    
    print(f"User Input: '2' (Talk later)")
    print(f"Response: {response}")
    
    # Verify state was cleared (conversation ended)
    mock_state_manager.clear_state.assert_called_once_with(mock_user.phone_number)
    
    # Verify response contains expected farewell message
    assert "GPS की समस्या बनी रहे तो कृपया हमसे संपर्क करें" in response
    assert "If GPS issues persist, please contact us" in response
    assert "धन्यवाद" in response
    
    print("✅ Conversation ended successfully")
    print("✅ State cleared properly")
    print("✅ Farewell message sent")
    
    return True

def test_gps_recheck_invalid_response():
    """Test GPS recheck with invalid user response."""
    print("\n" + "="*60)
    print("TEST: GPS Recheck - Invalid Response")
    print("="*60)
    
    # Mock dependencies
    mock_db = Mock()
    mock_state_manager = Mock(spec=StateManager)
    mock_user = Mock(spec=User)
    mock_user.phone_number = "+919876543210"
    mock_user.name = "Test Driver"
    
    # Set up state to be GPS_REPAIR_RECHECK
    mock_state = Mock()
    mock_state.current_step = ConversationStep.GPS_REPAIR_RECHECK.value
    mock_state_manager.get_state.return_value = mock_state
    mock_state_manager.get_context.return_value = {
        "vehicle_number": "MH12AB1234"
    }
    
    # Test invalid user input
    response = handle_support_message(
        user=mock_user,
        text_body="invalid response",
        state_manager=mock_state_manager,
        db=mock_db
    )
    
    print(f"User Input: 'invalid response'")
    print(f"Response: {response}")
    
    # Verify response contains options again
    assert "कृपया वैध विकल्प चुनें" in response
    assert "Please select a valid option" in response
    assert "1️⃣ दोबारा चेक करें / Check again" in response
    assert "2️⃣ बाद में बात करें / Talk later" in response
    
    # Verify state was not changed (no clear_state or set_state called)
    mock_state_manager.clear_state.assert_not_called()
    mock_state_manager.set_state.assert_not_called()
    
    print("✅ Invalid response handled correctly")
    print("✅ Options displayed again")
    print("✅ State remained unchanged")
    
    return True

def test_gps_recheck_verification_error():
    """Test GPS recheck when verification encounters an error."""
    print("\n" + "="*60)
    print("TEST: GPS Recheck - Verification Error Handling")
    print("="*60)
    
    # Mock dependencies
    mock_db = Mock()
    mock_state_manager = Mock(spec=StateManager)
    mock_user = Mock(spec=User)
    mock_user.phone_number = "+919876543210"
    mock_user.name = "Test Driver"
    
    # Set up state to be GPS_REPAIR_RECHECK
    mock_state = Mock()
    mock_state.current_step = ConversationStep.GPS_REPAIR_RECHECK.value
    mock_state_manager.get_state.return_value = mock_state
    mock_state_manager.get_context.return_value = {
        "vehicle_number": "MH12AB1234"
    }
    
    # Mock GPS verification to raise an exception
    with patch('app.services.support_flow_service._perform_gps_verification') as mock_gps_verify:
        mock_gps_verify.side_effect = Exception("Network error during verification")
        
        # Test user input "1" for check again (with error)
        response = handle_support_message(
            user=mock_user,
            text_body="1",
            state_manager=mock_state_manager,
            db=mock_db
        )
        
        print(f"User Input: '1' (Check again - with error)")
        print(f"Response: {response}")
        
        # Verify GPS verification was attempted
        mock_gps_verify.assert_called_once_with(mock_user.phone_number, mock_db, mock_state_manager)
        
        # Verify state was cleared due to error
        mock_state_manager.clear_state.assert_called_once_with(mock_user.phone_number)
        
        # Verify error response
        assert "GPS सत्यापन में त्रुटि हुई" in response
        assert "Error occurred during GPS verification" in response
        assert "मैन्युअल रूप से GPS स्थिति जांच लें" in response
        
        print("✅ Error during GPS verification handled correctly")
        print("✅ State cleared on error")
        print("✅ Error message provided to user")
        
    return True

def run_all_tests():
    """Run all GPS recheck functionality tests."""
    print("\n" + "🔧"*20 + " GPS RECHECK FUNCTIONALITY TESTS " + "🔧"*20)
    print("Testing the complete GPS re-verification flow after failed initial verification")
    
    tests = [
        ("GPS Recheck - Check Again", test_gps_recheck_check_again),
        ("GPS Recheck - Talk Later", test_gps_recheck_talk_later),
        ("GPS Recheck - Invalid Response", test_gps_recheck_invalid_response),
        ("GPS Recheck - Verification Error", test_gps_recheck_verification_error),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} - PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} - FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} - FAILED with exception: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print(f"GPS RECHECK FUNCTIONALITY TEST RESULTS")
    print("="*60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 ALL GPS RECHECK FUNCTIONALITY TESTS PASSED! 🎉")
        print("\nThe GPS re-verification system is working correctly:")
        print("• User can trigger new GPS verification with '1'")
        print("• User can end conversation with '2'")
        print("• Invalid responses are handled gracefully")
        print("• Errors during verification are managed properly")
        print("• State transitions work correctly")
        print("• Conversation flow keeps alive until successful or user ends it")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the implementation.")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)