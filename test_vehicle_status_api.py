#!/usr/bin/env python3
"""
Test script for Vehicle Status Update API

This script demonstrates how to use the new vehicle status update API
to update GPS coordinates, power state, and ignition state.
"""

import requests
import json
from typing import Dict, Any


class VehicleStatusAPITest:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}

    def update_vehicle_status(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update vehicle status using the API
        
        Args:
            vehicle_data: Dictionary with vehicle status fields
            
        Returns:
            API response
        """
        url = f"{self.base_url}/vehicles/status/update"
        
        try:
            print(f"🚀 Updating vehicle status...")
            print(f"📡 POST {url}")
            print(f"📋 Data: {json.dumps(vehicle_data, indent=2)}")
            
            response = requests.put(url, json=vehicle_data, headers=self.headers)
            
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Success!")
                print(f"📄 Response: {json.dumps(result, indent=2)}")
                return result
            else:
                print("❌ Error!")
                print(f"📄 Response: {response.text}")
                return {"error": response.text}
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {str(e)}")
            return {"error": str(e)}

    def get_vehicle_status(self, vehicle_number: str) -> Dict[str, Any]:
        """
        Get current vehicle status from database
        
        Args:
            vehicle_number: Vehicle registration number
            
        Returns:
            Current vehicle status
        """
        url = f"{self.base_url}/vehicles/status/{vehicle_number}"
        
        try:
            print(f"🔍 Getting vehicle status for {vehicle_number}...")
            print(f"📡 GET {url}")
            
            response = requests.get(url, headers=self.headers)
            
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Success!")
                print(f"📄 Response: {json.dumps(result, indent=2)}")
                return result
            else:
                print("❌ Error!")
                print(f"📄 Response: {response.text}")
                return {"error": response.text}
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {str(e)}")
            return {"error": str(e)}


def run_tests():
    """Run API tests with sample data"""
    
    print("🧪 Vehicle Status API Test Suite")
    print("=" * 50)
    
    # Initialize test client
    api = VehicleStatusAPITest()
    
    # Test data
    test_cases = [
        {
            "name": "Update all fields",
            "data": {
                "vehicle_number": "TEST-100",
                "latitude": 28.6139,
                "longitude": 77.2090,
                "power_state": "on",
                "ignition_state": "on"
            }
        },
        {
            "name": "Update only GPS coordinates",
            "data": {
                "vehicle_number": "TEST-100",
                "latitude": 28.7041,
                "longitude": 77.1025
            }
        },
        {
            "name": "Update only power and ignition",
            "data": {
                "vehicle_number": "TEST-100",
                "power_state": "off",
                "ignition_state": "off"
            }
        },
        {
            "name": "Invalid latitude (should fail)",
            "data": {
                "vehicle_number": "TEST-100",
                "latitude": 95.0,  # Invalid - outside -90 to 90 range
                "power_state": "on"
            }
        },
        {
            "name": "Invalid power state (should fail)",
            "data": {
                "vehicle_number": "TEST-100",
                "power_state": "invalid_state"
            }
        }
    ]
    
    # Run tests
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        print("-" * 30)
        
        # Update vehicle status
        result = api.update_vehicle_status(test_case['data'])
        
        # If update was successful, get current status
        if result.get("success"):
            print("\n🔍 Getting updated status...")
            api.get_vehicle_status(test_case['data']['vehicle_number'])
        
        print("\n" + "=" * 50)
    
    print("\n✅ Test suite completed!")


if __name__ == "__main__":
    run_tests()