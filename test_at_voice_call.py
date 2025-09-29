#!/usr/bin/env python3
"""
Direct Africa's Talking Voice Call test
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_voice_call():
    username = os.getenv('AFRICASTALKING_USERNAME', '')
    api_key = os.getenv('AFRICASTALKING_API_KEY', '')
    
    print("🧪 Testing Direct Africa's Talking Voice Call")
    print("=" * 50)
    
    if not username or not api_key:
        print("❌ Missing credentials")
        return
    
    phone_number = "+2347073152943"
    audio_url = "https://media.sd.ma/assabile/adhan_3435370/0bf83c80b583.mp3"
    
    # Africa's Talking Voice API
    api_url = "https://voice.africastalking.com/call"
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
        'apiKey': api_key
    }
    
    payload = {
        'username': username,
        'to': phone_number,
        'from': '+254711082500',  # Africa's Talking default caller ID
    }
    
    print(f"📞 Making call to: {phone_number}")
    print(f"🎵 Audio URL: {audio_url}")
    print(f"👤 Username: {username}")
    print()
    
    try:
        response = requests.post(api_url, headers=headers, data=payload, timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Response: {response.text}")
        
        if response.status_code == 200 or response.status_code == 201:
            try:
                result = response.json()
                print("✅ Voice call initiated!")
                print(f"Response: {result}")
            except:
                print("✅ Voice call response (non-JSON):", response.text)
        else:
            print(f"❌ Call failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_voice_call()