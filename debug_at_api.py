#!/usr/bin/env python3
"""
Debug Africa's Talking API calls
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def debug_at_api():
    username = os.getenv('AFRICASTALKING_USERNAME', '')
    api_key = os.getenv('AFRICASTALKING_API_KEY', '')
    
    print("🔍 Debug Africa's Talking API")
    print("=" * 40)
    print(f"Username: '{username}'")
    print(f"API Key: '{api_key[:12]}***{api_key[-8:]}'")
    print(f"Key length: {len(api_key)}")
    
    # Try the SMS endpoint with minimal payload
    api_url = "https://api.africastalking.com/version1/messaging"
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
        'apiKey': api_key
    }
    
    payload = {
        'username': username,
        'to': '2347073152943',  # Your number without +
        'message': 'Test message from Muadhin',
        'from': 'Muadhin'
    }
    
    print(f"\n📡 Testing SMS endpoint...")
    print(f"URL: {api_url}")
    print(f"Headers: {headers}")
    print(f"Payload: {payload}")
    
    try:
        response = requests.post(api_url, headers=headers, data=payload, timeout=30)
        
        print(f"\n📊 Response:")
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Body: {response.text}")
        
        if response.status_code == 401:
            print("\n❌ 401 - Authentication failed")
            print("Possible issues:")
            print("1. API key is incorrect")
            print("2. Username is incorrect") 
            print("3. Account is not activated")
            print("4. Sandbox mode restrictions")
            
        elif response.status_code == 201:
            print("✅ SMS would be sent successfully!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_at_api()