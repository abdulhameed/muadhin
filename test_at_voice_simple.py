#!/usr/bin/env python3
"""
Simple Africa's Talking Voice Call test without caller ID
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_simple_voice():
    username = os.getenv('AFRICASTALKING_USERNAME', '')
    api_key = os.getenv('AFRICASTALKING_API_KEY', '')
    
    print("🧪 Testing Simple Voice Call (no caller ID)")
    print("=" * 45)
    
    phone_number = "+2347073152943"
    
    api_url = "https://voice.africastalking.com/call"
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
        'apiKey': api_key
    }
    
    payload = {
        'username': username,
        'to': phone_number,
        # No 'from' field - let AT use default
    }
    
    print(f"📞 Calling: {phone_number}")
    print(f"👤 Username: {username}")
    print()
    
    try:
        response = requests.post(api_url, headers=headers, data=payload, timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Response: {response.text}")
        
        if response.status_code in [200, 201]:
            try:
                result = response.json()
                if result.get('entries'):
                    print("✅ Voice call initiated successfully!")
                    for entry in result['entries']:
                        print(f"   Phone: {entry.get('phoneNumber')}")
                        print(f"   Status: {entry.get('status')}")
                else:
                    error_msg = result.get('errorMessage', 'Unknown error')
                    print(f"❌ Call failed: {error_msg}")
            except:
                print("Response (non-JSON):", response.text)
        else:
            print(f"❌ Request failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_simple_voice()
