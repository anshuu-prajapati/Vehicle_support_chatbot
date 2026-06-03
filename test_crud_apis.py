#!/usr/bin/env python
"""
Quick test script for User and Vehicle CRUD APIs
Run this to test all endpoints
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def print_response(title, response):
    """Pretty print response"""
    print(f"\n{'='*60}")
    print(f"✓ {title}")
    print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)


def test_users_api():
    """Test User CRUD endpoints"""
    print("\n" + "="*60)
    print("TESTING USER CRUD ENDPOINTS")
    print("="*60)
    
    # 1. Create Manager
    manager_data = {
        "name": "Manager Raj",
        "phone_number": "+918882374849",
        "role": "manager"
    }
    r = requests.post(f"{BASE_URL}/users/", json=manager_data)
    print_response("Create Manager", r)
    manager_id = r.json().get("id")
    
    # 2. Create Supervisor
    supervisor_data = {
        "name": "Supervisor Amit",
        "phone_number": "+919876543210",
        "role": "supervisor"
    }
    r = requests.post(f"{BASE_URL}/users/", json=supervisor_data)
    print_response("Create Supervisor", r)
    supervisor_id = r.json().get("id")
    
    # 3. Create Driver
    driver_data = {
        "name": "Driver Vikram",
        "phone_number": "+918290323758",
        "role": "driver"
    }
    r = requests.post(f"{BASE_URL}/users/", json=driver_data)
    print_response("Create Driver", r)
    driver_id = r.json().get("id")
    
    # 4. Get All Users
    r = requests.get(f"{BASE_URL}/users/")
    print_response("Get All Users", r)
    
    # 5. Get Users by Role
    r = requests.get(f"{BASE_URL}/users/?role=manager")
    print_response("Get All Managers", r)
    
    # 6. Get Specific Managers List
    r = requests.get(f"{BASE_URL}/users/role/managers/list")
    print_response("Get Managers List", r)
    
    # 7. Get Supervisors List
    r = requests.get(f"{BASE_URL}/users/role/supervisors/list")
    print_response("Get Supervisors List", r)
    
    # 8. Get Drivers List
    r = requests.get(f"{BASE_URL}/users/role/drivers/list")
    print_response("Get Drivers List", r)
    
    # 9. Get User by ID
    r = requests.get(f"{BASE_URL}/users/{manager_id}")
    print_response(f"Get User by ID ({manager_id})", r)
    
    # 10. Get User by Phone
    r = requests.get(f"{BASE_URL}/users/phone/8882374849")
    print_response("Get User by Phone Number", r)
    
    # 11. Update User
    update_data = {
        "name": "Manager Raj Updated",
        "role": "manager"
    }
    r = requests.put(f"{BASE_URL}/users/{manager_id}", json=update_data)
    print_response("Update User", r)
    
    return manager_id, supervisor_id, driver_id


def test_vehicles_api(manager_id, supervisor_id, driver_id):
    """Test Vehicle CRUD endpoints"""
    print("\n" + "="*60)
    print("TESTING VEHICLE CRUD ENDPOINTS")
    print("="*60)
    
    # 1. Create Vehicle
    vehicle_data = {
        "vehicle_number": "DL-01-AB-1234",
        "manager_id": manager_id,
        "supervisor_id": supervisor_id,
        "driver_id": driver_id
    }
    r = requests.post(f"{BASE_URL}/vehicles/", json=vehicle_data)
    print_response("Create Vehicle", r)
    vehicle_id = r.json().get("id")
    
    # 2. Get All Vehicles
    r = requests.get(f"{BASE_URL}/vehicles/")
    print_response("Get All Vehicles", r)
    
    # 3. Get Vehicle by ID
    r = requests.get(f"{BASE_URL}/vehicles/{vehicle_id}")
    print_response(f"Get Vehicle by ID ({vehicle_id})", r)
    
    # 4. Get Vehicle by Number
    r = requests.get(f"{BASE_URL}/vehicles/number/DL-01-AB-1234")
    print_response("Get Vehicle by Number", r)
    
    # 5. Create Vehicle Status
    status_data = {
        "ign_state": "off",
        "mode": "not working",
        "location": "Noida Depot",
        "last_gps_time": "2026-06-03T12:00:00",
        "not_working_hours": 1
    }
    r = requests.post(f"{BASE_URL}/vehicles/{vehicle_id}/status", json=status_data)
    print_response("Create Vehicle Status", r)
    
    # 6. Get Vehicle Status
    r = requests.get(f"{BASE_URL}/vehicles/{vehicle_id}/status")
    print_response("Get Vehicle Status", r)
    
    # 7. Get Not Working Vehicles
    r = requests.get(f"{BASE_URL}/vehicles/status/not-working/list")
    print_response("Get Not Working Vehicles", r)
    
    # 8. Update Vehicle
    update_data = {
        "vehicle_number": "DL-01-AB-5678"
    }
    r = requests.put(f"{BASE_URL}/vehicles/{vehicle_id}", json=update_data)
    print_response("Update Vehicle", r)
    
    return vehicle_id


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("AI SUPPORT SYSTEM - API TESTING")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    
    try:
        # Test Users API
        manager_id, supervisor_id, driver_id = test_users_api()
        
        # Test Vehicles API
        vehicle_id = test_vehicles_api(manager_id, supervisor_id, driver_id)
        
        # 9. Delete Vehicle (optional)
        print("\n" + "="*60)
        print("OPTIONAL: DELETE OPERATIONS")
        print("="*60)
        
        delete_vehicle = input("Delete test vehicle? (y/n): ").lower() == 'y'
        if delete_vehicle:
            r = requests.delete(f"{BASE_URL}/vehicles/{vehicle_id}")
            print_response("Delete Vehicle", r)
        
        delete_user = input("Delete test manager? (y/n): ").lower() == 'y'
        if delete_user:
            r = requests.delete(f"{BASE_URL}/users/{manager_id}")
            print_response("Delete User", r)
        
        print("\n" + "="*60)
        print("✓ ALL TESTS COMPLETED")
        print("="*60)
        print("\nFor full API documentation, see: API_DOCUMENTATION.md")
        
    except requests.exceptions.ConnectionError:
        print(f"\n✗ ERROR: Could not connect to {BASE_URL}")
        print("Make sure the FastAPI server is running:")
        print("  uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")


if __name__ == "__main__":
    main()
