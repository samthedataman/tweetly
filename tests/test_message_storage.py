#!/usr/bin/env python3
"""Test message storage endpoint in detail"""

import requests
import jwt
from datetime import datetime, timedelta, timezone
import time
import json

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_WALLET = "0x742d35cc6634c0532925a3b8d042c18e9c7b8c8d"

# Create auth token
payload = {
    "wallet": TEST_WALLET,
    "user_id": f"test_user_{TEST_WALLET[-8:]}",
    "method": "wallet",
    "session_id": "test_session_123",
    "total_earnings": 0.0,
    "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    "iat": datetime.now(timezone.utc)
}
JWT_SECRET = "contextly-secret-key-change-in-production"
auth_token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

# Setup session
session = requests.Session()
session.headers.update({
    'Authorization': f'Bearer {auth_token}',
    'Content-Type': 'application/json'
})

print("🔍 TESTING MESSAGE STORAGE ENDPOINT")
print("=" * 50)

# Test message storage
session_id = f"test_session_{int(time.time())}"
message_payload = {
    "message": {
        "id": f"test_msg_{int(time.time())}",
        "session_id": session_id,
        "role": "user",
        "text": "This is a test message for comprehensive backend testing",
        "timestamp": int(time.time() * 1000),
        "platform": "claude"
    },
    "session_id": session_id,
    "wallet": TEST_WALLET
}

print(f"📤 Sending message payload:")
print(json.dumps(message_payload, indent=2))

try:
    response = session.post(f"{API_BASE_URL}/v1/conversations/message", 
                           json=message_payload)
    
    print(f"\n📥 Response Status: {response.status_code}")
    print(f"📥 Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        print(f"✅ Success: {response.json()}")
    else:
        print(f"❌ Error Response: {response.text}")
        
        # Try to parse error details
        try:
            error_data = response.json()
            print(f"❌ Error Details: {json.dumps(error_data, indent=2)}")
        except:
            pass
            
except Exception as e:
    print(f"❌ Exception: {e}")

print("\n" + "=" * 50)