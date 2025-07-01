#!/usr/bin/env python3
"""
Test a single endpoint with detailed debugging
"""

import requests
import jwt
from datetime import datetime, timedelta, timezone
import json

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_WALLET = "0x742d35cc6634c0532925a3b8d042c18e9c7b8c8d"

# Create auth token with all fields
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

print("🔍 TESTING /v1/sessions/history ENDPOINT")
print("=" * 50)
print(f"Token payload: {json.dumps({k: str(v) for k, v in payload.items()}, indent=2)}")

# Test the endpoint
session = requests.Session()
session.headers.update({
    'Authorization': f'Bearer {auth_token}',
    'Content-Type': 'application/json'
})

print("\nMaking request to /v1/sessions/history...")
response = session.get(f"{API_BASE_URL}/v1/sessions/history", params={'limit': 5})

print(f"\nStatus Code: {response.status_code}")
print(f"Headers: {dict(response.headers)}")
print(f"Response Body: {response.text}")

# If it's still 500, try with different parameters
if response.status_code == 500:
    print("\nTrying without parameters...")
    response2 = session.get(f"{API_BASE_URL}/v1/sessions/history")
    print(f"Status Code: {response2.status_code}")
    print(f"Response Body: {response2.text}")

# Also test the health check to ensure API is responding
print("\nTesting health check...")
health_response = session.get(f"{API_BASE_URL}/")
print(f"Health check status: {health_response.status_code}")
print(f"Health check response: {health_response.json() if health_response.status_code == 200 else health_response.text}")