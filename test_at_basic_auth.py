#!/usr/bin/env python3
"""
Test Africa's Talking with Basic Auth (alternative method)
"""

import os
import requests
import base64
from dotenv import load_dotenv

load_dotenv()

def test_basic_auth():
    username = os.getenv('AFRICASTALKING_USERNAME', '')
    api_key = os.getenv('AFRICASTALKING_API_KEY', '')
    
    print("🔍 Testing Africa's Talking with Basic Auth")
    print("=" * 45)
    
    # Try Basic Authentication instead of apiKey header
    auth_string = base64.b64encode(f"{username}:{api_key}".encode()).decode()
    
    api_url = "https://api.africastalking.com/version1/messaging"
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {auth_string}'
    }
    
    payload = {
        'username': username,
        'to': '2347073152943',
        'message': 'Test SMS via Basic Auth',
        'from': 'Muadhin'
    }
    
    try:
        response = requests.post(api_url, headers=headers, data=payload, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 201:
            print("✅ Basic Auth works!")
        else:
            print("❌ Basic Auth also failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def check_sandbox_info():
    print("\n📋 Sandbox Account Information:")
    print("- Sandbox accounts are for testing only")
    print("- They might have different API endpoints")  
    print("- SMS might not actually send but should return 201")
    print("- Check: https://developers.africastalking.com/sandbox")
    
    username = os.getenv('AFRICASTALKING_USERNAME', '')
    api_key = os.getenv('AFRICASTALKING_API_KEY', '')
    
    print(f"\n🔑 Current Config:")
    print(f"Username: {username}")
    print(f"API Key valid format: {'✅' if api_key.startswith('atsk_') and len(api_key) > 50 else '❌'}")
    
    print(f"\n💡 Recommendations:")
    print("1. Double-check your sandbox API key in AT dashboard")
    print("2. Ensure sandbox account is active") 
    print("3. Try creating a live account if sandbox has issues")
    print("4. Contact Africa's Talking support if issues persist")

if __name__ == "__main__":
    test_basic_auth()
    check_sandbox_info()