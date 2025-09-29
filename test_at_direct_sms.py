#!/usr/bin/env python3
"""
Direct Africa's Talking SMS test - bypassing Django
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_direct_sms():
    username = os.getenv('AFRICASTALKING_USERNAME', '')
    api_key = os.getenv('AFRICASTALKING_API_KEY', '')
    sender_id = os.getenv('AFRICASTALKING_SENDER_ID', 'Muadhin')
    
    print("🧪 Testing Direct Africa's Talking SMS API")
    print("=" * 50)
    
    if not username or not api_key:
        print("❌ Missing credentials")
        return
    
    # Test phone number (remove + for AT API)
    phone_number = "2347073152943"  # Without +
    message = "🧪 Direct API test from Muadhin via Africa's Talking SMS"
    
    # Africa's Talking SMS API
    api_url = "https://api.africastalking.com/version1/messaging"
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
        'apiKey': api_key
    }
    
    payload = {
        'username': username,
        'to': phone_number,
        'message': message,
        'from': sender_id
    }
    
    print(f"📱 Sending SMS to: +{phone_number}")
    print(f"📝 Message: {message}")
    print(f"🏷️ Sender ID: {sender_id}")
    print(f"👤 Username: {username}")
    print()
    
    try:
        response = requests.post(api_url, headers=headers, data=payload, timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Response: {response.text}")
        print()
        
        if response.status_code == 201:
            result = response.json()
            print("✅ Request successful!")
            print(f"Response JSON: {result}")
            
            sms_data = result.get('SMSMessageData', {})
            recipients = sms_data.get('Recipients', [])
            
            if recipients:
                for i, recipient in enumerate(recipients):
                    print(f"\n📱 Recipient {i+1}:")
                    print(f"   Number: {recipient.get('number', 'N/A')}")
                    print(f"   Status: {recipient.get('status', 'N/A')}")
                    print(f"   Cost: {recipient.get('cost', 'N/A')}")
                    print(f"   Message ID: {recipient.get('messageId', 'N/A')}")
            else:
                print("⚠️ No recipients found in response")
        else:
            print(f"❌ Request failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_direct_sms()