#!/usr/bin/env python3
"""
Debug the remaining 2 failing endpoints
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

print("🔍 DEBUGGING REMAINING 2 FAILING ENDPOINTS")
print("=" * 50)

# Test 1: Sankey Generation
print("\n1. Testing /v1/journeys/sankey")
try:
    response = session.post(f"{API_BASE_URL}/v1/journeys/sankey", 
                           json={'wallet': TEST_WALLET})
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Success: {data}")
    else:
        print(f"   Error Response: {response.text}")
except Exception as e:
    print(f"   Exception: {e}")

# Test 2: Graph Visualization  
print("\n2. Testing /v1/graph/visualize")
try:
    response = session.post(f"{API_BASE_URL}/v1/graph/visualize", 
                           json={'wallet': TEST_WALLET})
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Success: {data}")
    else:
        print(f"   Error Response: {response.text}")
except Exception as e:
    print(f"   Exception: {e}")

print("\n" + "=" * 50)