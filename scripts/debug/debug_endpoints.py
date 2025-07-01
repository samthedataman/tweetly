#!/usr/bin/env python3
"""
Debug specific failing endpoints to see actual error messages
"""

import requests
import jwt
from datetime import datetime, timedelta

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_WALLET = "0x742d35cc6634c0532925a3b8d042c18e9c7b8c8d"

# Create auth token
payload = {
    "wallet": TEST_WALLET,
    "user_id": f"test_user_{TEST_WALLET[-8:]}",
    "exp": datetime.utcnow() + timedelta(hours=24)
}
JWT_SECRET = "contextly-secret-key-change-in-production"
auth_token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

# Setup session
session = requests.Session()
session.headers.update({
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {auth_token}'
})

print("🔍 DEBUGGING FAILING ENDPOINTS")
print("=" * 50)

# Test 1: Sankey Generation
print("\n1. Testing /v1/journeys/sankey")
try:
    response = session.post(f"{API_BASE_URL}/v1/journeys/sankey", 
                           json={'wallet': TEST_WALLET})
    print(f"   Status: {response.status_code}")
    if response.status_code != 200:
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"   Error: {e}")

# Test 2: Insights Generation
print("\n2. Testing /v1/insights/generate")
try:
    response = session.post(f"{API_BASE_URL}/v1/insights/generate", 
                           params={'time_range': 7})
    print(f"   Status: {response.status_code}")
    if response.status_code != 200:
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"   Error: {e}")

# Test 3: Session History
print("\n3. Testing /v1/sessions/history")
try:
    response = session.get(f"{API_BASE_URL}/v1/sessions/history",
                          params={'limit': 10})
    print(f"   Status: {response.status_code}")
    if response.status_code != 200:
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 50)