#!/usr/bin/env python3
"""
Test authentication directly
"""

import requests
import jwt
from datetime import datetime, timedelta, timezone

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_WALLET = "0x742d35cc6634c0532925a3b8d042c18e9c7b8c8d"

# Create auth token
payload = {
    "wallet": TEST_WALLET,
    "user_id": f"test_user_{TEST_WALLET[-8:]}",
    "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    "iat": datetime.now(timezone.utc)
}
JWT_SECRET = "contextly-secret-key-change-in-production"
auth_token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

print("🔐 TESTING AUTHENTICATION")
print("=" * 50)
print(f"Token payload: {payload}")
print(f"Token: {auth_token[:50]}...")

# Test with a simple authenticated endpoint
session = requests.Session()
session.headers.update({
    'Authorization': f'Bearer {auth_token}'
})

print("\nTesting authenticated endpoint: /v1/auto-mode/status/{wallet}")
response = session.get(f"{API_BASE_URL}/v1/auto-mode/status/{TEST_WALLET}")
print(f"Status: {response.status_code}")
print(f"Response: {response.json() if response.status_code == 200 else response.text}")

print("\nTesting /v1/sessions/history with minimal request")
response = session.get(f"{API_BASE_URL}/v1/sessions/history")
print(f"Status: {response.status_code}")
if response.status_code != 200:
    print(f"Response: {response.text}")
    print(f"Headers: {response.headers}")