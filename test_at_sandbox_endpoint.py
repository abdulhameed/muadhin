#!/usr/bin/env python3
"""
Test Africa's Talking sandbox with different endpoints
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_sandbox_endpoints():
    username = os.getenv('AFRICASTALKING_USERNAME', '')
    api_key = os.getenv('AFRICASTALKING_API_KEY', '')
    
    print("🔍 Testing Different Africa's Talking Endpoints")
    print("=" * 50)
    
    # Different possible endpoints for sandbox
    endpoints = [
        "https://api.africastalking.com/version1/messaging",  # Standard
        "https://api.sandbox.africastalking.com/version1/messaging",  # Sandbox specific
        "https://content.africastalking.com/version1/messaging",  # Alternative
    ]
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
        'apiKey': api_key
    }
    
    payload = {
        'username': username,
        'to': '2347073152943',
        'message': 'Test message',
        'from': 'Muadhin'
    }
    
    for i, endpoint in enumerate(endpoints, 1):
        print(f"\n🧪 Test {i}: {endpoint}")
        try:
            response = requests.post(endpoint, headers=headers, data=payload, timeout=15)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 201:
                print("   ✅ SUCCESS! This endpoint works")
                print(f"   Response: {response.text}")
                return endpoint
            elif response.status_code == 401:
                print("   ❌ 401 Unauthorized")
            elif response.status_code == 404:
                print("   ❌ 404 Not Found - Wrong endpoint")
            else:
                print(f"   ❓ Unexpected: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Network error: {e}")
    
    print(f"\n💡 None of the endpoints worked with your credentials.")
    print(f"📋 This suggests the issue is with the API key or username, not the endpoint.")
    
    return None

def suggest_next_steps():
    print(f"\n🛠️ Troubleshooting Steps:")
    print("1. ✅ Verify your sandbox API key is exactly as shown in AT dashboard")
    print("2. ✅ Ensure username is 'sandbox' (not your actual username)")
    print("3. ✅ Check if sandbox account needs phone verification")
    print("4. ✅ Try generating a completely new API key")
    print("5. ✅ Consider creating a live account with $1-2 credit for testing")
    
    print(f"\n📞 Alternative: Your debug mode works perfectly!")
    print("   You can develop and test your entire application logic")
    print("   without needing real API calls right now.")

if __name__ == "__main__":
    working_endpoint = test_sandbox_endpoints()
    if not working_endpoint:
        suggest_next_steps()