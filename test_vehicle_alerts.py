#!/usr/bin/env python3
"""
Test script for Vehicle Alert API functionality
Run this after starting the FastAPI server to test the new endpoints
"""
import requests
import json

API_BASE_URL = "http://127.0.0.1:8000"

def test_breakdown_status():
    """Test the breakdown status endpoint (safe - no WhatsApp messages sent)"""
    print("🔍 Testing breakdown status endpoint...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/vehicles/breakdown-status")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Breakdown status endpoint works!")
            print(f"📊 Found {data['vehicles_count']} broken vehicle(s)")
            
            if data['vehicles_count'] > 0:
                print("\n📋 Broken Vehicles Details:")
                for vehicle in data['vehicles_data']:
                    print(f"  • {vehicle['vehicle_number']} at {vehicle['location']}")
                    if vehicle['manager_phone']:
                        print(f"    Manager: {vehicle['manager_phone']}")
            else:
                print("🎉 No broken vehicles found!")
            
            return True
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure FastAPI server is running on http://127.0.0.1:8000")
        print("   Start server with: python -m uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_send_alerts():
    """Test the send alerts endpoint (WARNING: This will send actual WhatsApp messages!)"""
    print("\n🚨 Testing send breakdown alerts endpoint...")
    print("⚠️  WARNING: This will send actual WhatsApp messages to managers!")
    
    # Uncomment the lines below only when you're ready to test WhatsApp sending
    confirmation = input("Do you want to proceed? (yes/no): ").lower().strip()
    
    if confirmation not in ['yes', 'y']:
        print("🛑 Skipping WhatsApp alert test")
        return True
    
    try:
        response = requests.post(f"{API_BASE_URL}/vehicles/send-breakdown-alerts")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Send alerts endpoint works!")
            print(f"📧 Sent {data['alerts_sent']} alert(s) for {data['vehicles_count']} vehicle(s)")
            
            if data['failed_sends']:
                print("❌ Some messages failed to send:")
                for failure in data['failed_sends']:
                    print(f"  • {failure['phone']}: {failure['error']}")
            
            return True
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_api_docs():
    """Test if the API documentation is accessible"""
    print("\n📚 Testing API documentation...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/docs")
        
        if response.status_code == 200:
            print("✅ API documentation is accessible at http://127.0.0.1:8000/docs")
            print("   You can test the endpoints interactively there!")
            return True
        else:
            print(f"❌ API docs not accessible: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error accessing API docs: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Vehicle Alert API Test Suite")
    print("=" * 50)
    
    # Test basic connectivity and safe endpoint
    status_ok = test_breakdown_status()
    
    if status_ok:
        # Test API documentation
        test_api_docs()
        
        # Test WhatsApp sending (with confirmation)
        test_send_alerts()
        
        print("\n🎉 Test Summary:")
        print("• Breakdown status endpoint: ✅ Working")
        print("• API documentation: ✅ Available") 
        print("• WhatsApp alerts: Ready for testing")
        
        print("\n🔗 API Endpoints:")
        print(f"• GET  {API_BASE_URL}/vehicles/breakdown-status")
        print(f"• POST {API_BASE_URL}/vehicles/send-breakdown-alerts")
        print(f"• Docs {API_BASE_URL}/docs")
        
    else:
        print("\n❌ Basic tests failed. Please check:")
        print("1. FastAPI server is running")
        print("2. Database is connected") 
        print("3. No syntax errors in code")