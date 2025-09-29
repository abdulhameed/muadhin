#!/usr/bin/env python3
"""
Simple Africa's Talking API test script
Run: python test_at_credentials.py
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_africastalking_credentials():
    username = os.getenv('AFRICASTALKING_USERNAME', '')
    api_key = os.getenv('AFRICASTALKING_API_KEY', '')
    
    print("🔍 Testing Africa's Talking Credentials")
    print("=" * 40)
    print(f"Username: {username}")
    print(f"API Key: {api_key[:8]}***{api_key[-4:] if len(api_key) > 4 else '***'}")
    
    if not username or not api_key:
        print("❌ Missing credentials in .env file")
        return
    
    # Test with Application Data endpoint (doesn't send SMS/make calls)
    try:
        url = "https://api.africastalking.com/version1/user"
        headers = {
            'Accept': 'application/json',
            'apiKey': api_key
        }
        params = {'username': username}
        
        print("\n🧪 Testing API connectivity...")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Credentials are VALID!")
            print(f"Account Balance: {data.get('UserData', {}).get('balance', 'Unknown')}")
            return True
        elif response.status_code == 401:
            print("❌ 401 UNAUTHORIZED - Invalid credentials")
            print("💡 Check your username and API key in Africa's Talking dashboard")
            return False
        else:
            print(f"❌ Unexpected response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Network error: {e}")
        return False

if __name__ == "__main__":
    test_africastalking_credentials()