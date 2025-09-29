#!/usr/bin/env python3
"""
Direct Africa's Talking SMS test without custom sender ID
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_sms_no_sender_id():
    username = os.getenv('AFRICASTALKING_USERNAME', '')
    api_key = os.getenv('AFRICASTALKING_API_KEY', '')
    
    print("🧪 Testing SMS without custom sender ID")
    print("=" * 40)
    
    phone_number = "2347073152943"  # Without +
    message = "🧪 Test from Africa's Talking SMS API (no custom sender ID)"
    
    api_url = "https://api.africastalking.com/version1/messaging"
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
        'apiKey': api_key
    }
    
    payload = {
        'username': username,
        'to': phone_number,
        'message': message
        # No 'from' field - let AT use default
    }
    
    print(f"📱 Sending SMS to: +{phone_number}")
    print(f"📝 Message: {message}")
    print(f"👤 Username: {username}")
    print("🏷️ Sender ID: (default)")
    print()
    
    try:
        response = requests.post(api_url, headers=headers, data=payload, timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Response: {response.text}")
        
        if response.status_code == 201:
            result = response.json()
            print("✅ Request successful!")
            
            sms_data = result.get('SMSMessageData', {})
            recipients = sms_data.get('Recipients', [])
            
            if recipients:
                for recipient in recipients:
                    print(f"\n📱 Recipient Details:")
                    print(f"   Number: {recipient.get('number', 'N/A')}")
                    print(f"   Status: {recipient.get('status', 'N/A')}")
                    print(f"   Cost: {recipient.get('cost', 'N/A')}")
                    print(f"   Message ID: {recipient.get('messageId', 'N/A')}")
                    
                    if recipient.get('status') == 'Success':
                        print("🎉 SMS sent successfully! Check your phone.")
            else:
                print(f"⚠️ No recipients. Message: {sms_data.get('Message', 'Unknown')}")
        else:
            print(f"❌ Request failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_sms_no_sender_id()