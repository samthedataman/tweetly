#!/usr/bin/env python3
"""
Test user creation and message storage
"""

import requests
import json
import uuid
from datetime import datetime, timezone, timedelta
import time
import jwt

# Configuration
API_BASE_URL = "http://localhost:8000"
JWT_SECRET = "contextly-secret-key-change-in-production"

# Generate proper JWT token
def generate_test_token(wallet_address, user_id):
    """Generate a valid JWT token for testing"""
    UTC = timezone.utc
    payload = {
        "wallet": wallet_address,
        "user_id": user_id,
        "exp": datetime.now(UTC) + timedelta(days=7),
        "iat": datetime.now(UTC)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

# Test with a new wallet address
TEST_WALLET = f"0x{uuid.uuid4().hex[:40]}"  # Generate random wallet
TEST_USER_ID = f"test_user_{TEST_WALLET[-8:]}"
TEST_SESSION_ID = f"test_session_{uuid.uuid4().hex[:8]}"
TEST_CONVERSATION_ID = f"conv_{uuid.uuid4().hex[:8]}"

# Generate valid JWT token
TEST_TOKEN = generate_test_token(TEST_WALLET, TEST_USER_ID)

# Headers with auth token
headers = {
    "Authorization": f"Bearer {TEST_TOKEN}",
    "Content-Type": "application/json",
    "X-Wallet-Address": TEST_WALLET
}

print(f"🧪 Testing User Creation & Message Storage")
print(f"🔑 New Wallet: {TEST_WALLET}")
print(f"📝 User ID: {TEST_USER_ID}")
print("=" * 60)

# Step 1: Check user doesn't exist
print("\n1️⃣ Checking user doesn't exist...")
response = requests.get(f"{API_BASE_URL}/v1/stats/{TEST_WALLET}", headers=headers)
print(f"   Status: {response.status_code} (expecting 404)")

# Step 2: Save a message (should create user automatically)
print("\n2️⃣ Saving message (should auto-create user)...")
msg_id = f"msg_{uuid.uuid4().hex[:8]}"
message_data = {
    "message": {
        "id": msg_id,
        "conversation_id": TEST_CONVERSATION_ID,
        "session_id": TEST_SESSION_ID,
        "role": "user",
        "text": "Test message for user creation",
        "timestamp": int(time.time()),
        "platform": "claude"
    },
    "conversation_id": TEST_CONVERSATION_ID,
    "session_id": TEST_SESSION_ID,
    "wallet": TEST_WALLET
}

response = requests.post(
    f"{API_BASE_URL}/v1/conversations/message",
    headers=headers,
    json=message_data
)
print(f"   Status: {response.status_code}")
if response.status_code != 200:
    print(f"   Response: {response.text}")
else:
    print(f"   Success: {json.dumps(response.json(), indent=2)}")

# Step 3: Check if user was created
print("\n3️⃣ Checking if user was created...")
response = requests.get(f"{API_BASE_URL}/v1/stats/{TEST_WALLET}", headers=headers)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    print(f"   User data: {json.dumps(response.json(), indent=2)}")

# Step 4: Check conversation history
print("\n4️⃣ Checking conversation history...")
response = requests.get(
    f"{API_BASE_URL}/v1/conversations/history",
    headers=headers,
    params={"wallet": TEST_WALLET, "limit": 10}
)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Conversations: {data.get('total', 0)}")

print("\n✅ Test complete!")