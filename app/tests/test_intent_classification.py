"""
Tests for intent classification service
"""
import pytest
from app.services.intent_classification_service import (
    classify_customer_intent,
    _regex_classify,
    get_issue_type_display_name
)


class TestIntentClassification:
    """Test intent classification functionality"""
    
    def test_regex_workshop_english(self):
        """Test workshop classification with English text"""
        result = _regex_classify("Vehicle is in workshop")
        assert result == "WORKSHOP"
    
    def test_regex_workshop_hindi(self):
        """Test workshop classification with Hindi text"""
        result = _regex_classify("गाड़ी वर्कशॉप में है")
        assert result == "WORKSHOP"
    
    def test_regex_accident_english(self):
        """Test accident classification"""
        result = _regex_classify("Accident ho gaya hai")
        assert result == "ACCIDENT"
    
    def test_regex_battery_disconnect(self):
        """Test battery disconnect classification"""
        result = _regex_classify("Battery nikal di maintenance ke liye")
        assert result == "BATTERY_DISCONNECT"
    
    def test_regex_gps_removed_hindi(self):
        """Test GPS removed classification"""
        result = _regex_classify("GPS nikal gaya hai")
        assert result == "GPS_REMOVED"
    
    def test_regex_gps_damaged(self):
        """Test GPS damaged classification"""
        result = _regex_classify("GPS toot gaya hai")
        assert result == "GPS_DAMAGED"
    
    def test_regex_vehicle_running(self):
        """Test vehicle running classification"""
        result = _regex_classify("Gaadi chal rahi hai, driver driving kar raha hai")
        assert result == "VEHICLE_RUNNING"
    
    def test_regex_vehicle_standing(self):
        """Test vehicle standing classification"""
        result = _regex_classify("Vehicle khadi hai, driver leave par hai")
        assert result == "VEHICLE_STANDING"
    
    def test_regex_unknown(self):
        """Test unknown classification for unclear messages"""
        result = _regex_classify("Kuch samajh nahi aa raha")
        assert result == "UNKNOWN"
    
    def test_display_name_english(self):
        """Test display name in English"""
        name = get_issue_type_display_name("WORKSHOP", "english")
        assert name == "Workshop"
    
    def test_display_name_hindi(self):
        """Test display name in Hindi"""
        name = get_issue_type_display_name("WORKSHOP", "hindi")
        assert name == "वर्कशॉप"
    
    def test_display_name_both(self):
        """Test display name in both languages"""
        name = get_issue_type_display_name("WORKSHOP", "both")
        assert "वर्कशॉप" in name and "Workshop" in name
    
    def test_multiple_workshops_phrases(self):
        """Test various ways to say workshop"""
        phrases = [
            "Vehicle workshop mein hai",
            "Repair center mein rakha hai",
            "Service center mein hai",
            "गाड़ी मरम्मत के लिए है"
        ]
        for phrase in phrases:
            result = _regex_classify(phrase)
            assert result == "WORKSHOP", f"Failed for: {phrase}"
    
    def test_accident_variations(self):
        """Test accident variations"""
        phrases = [
            "Accident ke baad workshop mein hai",
            "Collision ho gaya",
            "टक्कर लग गई"
        ]
        for phrase in phrases:
            result = _regex_classify(phrase)
            assert result == "ACCIDENT", f"Failed for: {phrase}"
    
    def test_gps_removed_variations(self):
        """Test GPS removed variations"""
        phrases = [
            "GPS nikal gaya",
            "GPS remove ho gaya",
            "GPS detach ho gaya"
        ]
        for phrase in phrases:
            result = _regex_classify(phrase)
            assert result == "GPS_REMOVED", f"Failed for: {phrase}"
    
    def test_classification_returns_tuple(self):
        """Test that classify_customer_intent returns tuple with method"""
        # This will use regex since we're testing without LLM
        result, method = classify_customer_intent("Vehicle workshop mein hai")
        assert isinstance(result, str)
        assert method in ["LLM", "REGEX"]
        assert result in [
            "WORKSHOP", "ACCIDENT", "BATTERY_DISCONNECT",
            "GPS_REMOVED", "GPS_DAMAGED", "VEHICLE_RUNNING",
            "VEHICLE_STANDING", "UNKNOWN"
        ]


# Sample test messages for manual testing
SAMPLE_MESSAGES = {
    "WORKSHOP": [
        "Vehicle workshop mein hai",
        "गाड़ी वर्कशॉप में मरम्मत के लिए है",
        "Repair center mein rakhi hui hai"
    ],
    "ACCIDENT": [
        "Accident ho gaya hai",
        "टक्कर लग गई थी",
        "Collision ke baad damage hui hai"
    ],
    "BATTERY_DISCONNECT": [
        "Battery nikali hui hai maintenance ke liye",
        "बैटरी हटा दी है",
        "Battery replacement kar rahe hain"
    ],
    "GPS_REMOVED": [
        "GPS nikal gaya hai",
        "GPS remove ho gaya",
        "GPS detach kar diya"
    ],
    "GPS_DAMAGED": [
        "GPS toot gaya hai",
        "GPS khrab ho gaya",
        "Device damage ho gaya"
    ],
    "VEHICLE_RUNNING": [
        "Gaadi chal rahi hai",
        "Driver vehicle chala raha hai",
        "वाहन चल रहा है"
    ],
    "VEHICLE_STANDING": [
        "Vehicle khadi hai",
        "Driver leave par hai",
        "गाड़ी पार्क है"
    ],
}


if __name__ == "__main__":
    # Run manual tests with sample messages
    print("Testing Intent Classification\n")
    print("=" * 50)
    
    for expected_type, messages in SAMPLE_MESSAGES.items():
        print(f"\n{expected_type}:")
        for msg in messages:
            result, method = classify_customer_intent(msg)
            status = "✓" if result == expected_type else "✗"
            print(f"  {status} '{msg}' → {result} ({method})")
