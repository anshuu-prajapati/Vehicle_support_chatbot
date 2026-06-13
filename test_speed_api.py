#!/usr/bin/env python3
"""
Test script to verify the speed field is available in the vehicle status update API.
Usage: python test_speed_api.py
"""

import requests
import json

# API endpoint
url = "http://127.0.0.1:8000/vehicles/status/update"

# Test request with speed field
test_request = {
    "vehicle_number": "TEST-100",
    "latitude": 55.6139,
    "longitude": 42.2090,
    "speed": 45.5,  # New speed field in km/h
    "power_state": "off",
    "ignition_state": "on"
}

print("Testing Vehicle Status Update API with Speed Field")
print("=" * 50)
print(f"URL: {url}")
print(f"Request Body:")
print(json.dumps(test_request, indent=2))

try:
    response = requests.put(url, json=test_request)
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Body:")
    
    if response.status_code == 200:
        response_data = response.json()
        print(json.dumps(response_data, indent=2))
        
        # Check if speed was in updated fields
        updated_fields = response_data.get("updated_fields", {})
        if "speed" in updated_fields:
            print("\n✅ SUCCESS: Speed field was successfully updated!")
            print(f"   Speed updated from {updated_fields['speed']['old_value']} to {updated_fields['speed']['new_value']}")
        else:
            print("\n⚠️  Speed field was not found in updated_fields")
            
    else:
        print(response.text)
        
except requests.exceptions.ConnectionError:
    print("\n❌ ERROR: Could not connect to the API server.")
    print("   Make sure the server is running on http://127.0.0.1:8000")
    
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")

print("\n" + "=" * 50)
print("Test completed.")