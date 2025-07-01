#!/usr/bin/env python3
"""
Detailed test for message saving to see exact error
"""

import requests
import json
import uuid
import time
import jwt
from datetime import datetime, timezone, timedelta

API_BASE_URL = "http://localhost:8000"
JWT_SECRET = "contextly-secret-key-change-in-production"

# Generate token
def generate_test_token(wallet_address, user_id):
    UTC = timezone.utc
    payload = {
        "wallet": wallet_address,
        "user_id": user_id,
        "exp": datetime.now(UTC) + timedelta(days=7),
        "iat": datetime.now(UTC)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

# Test data
TEST_WALLET = "0x87ac324d24a2ee59456321c37c3560a824f375b3"
TEST_USER_ID = f"test_user_{TEST_WALLET[-8:]}"
TEST_TOKEN = generate_test_token(TEST_WALLET, TEST_USER_ID)

headers = {
    "Authorization": f"Bearer {TEST_TOKEN}",
    "Content-Type": "application/json",
    "X-Wallet-Address": TEST_WALLET
}

print("🧪 Testing Message Save Endpoint")
print("=" * 60)

# Create message
msg_id = f"msg_{uuid.uuid4().hex[:8]}"
session_id = f"session_{uuid.uuid4().hex[:8]}"
conversation_id = f"conv_{uuid.uuid4().hex[:8]}"

message_data = {
    "message": {
        "id": msg_id,
        "conversation_id": conversation_id,
        "session_id": session_id,
        "role": "user",
        "text": "Test message",
        "timestamp": int(time.time()),
        "platform": "claude"
    },
    "conversation_id": conversation_id,
    "session_id": session_id,
    "wallet": TEST_WALLET
}

print(f"📤 Sending message:")
print(json.dumps(message_data, indent=2))
print("\n" + "=" * 60)

response = requests.post(
    f"{API_BASE_URL}/v1/conversations/message",
    headers=headers,
    json=message_data
)

print(f"\n📥 Response Status: {response.status_code}")
print(f"📥 Response Headers: {dict(response.headers)}")

if response.status_code == 200:
    print(f"✅ Success: {json.dumps(response.json(), indent=2)}")
else:
    print(f"❌ Error Response Text: {response.text}")
    print(f"❌ Response Content: {response.content}")
    
    # Try to get more details
    if response.status_code == 500:
        print("\n⚠️  500 Internal Server Error - Check backend logs for details")