#!/usr/bin/env python3
"""
Simple test to check what's wrong with the API
"""

import requests
import json

API_BASE_URL = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ3YWxsZXQiOiIweDg3YWMzMjRkMjRhMmVlNTk0NTYzMjFjMzdjMzU2MGE4MjRmMzc1YjMiLCJ1c2VyX2lkIjoiMDNiY2I2ZDMtOTVhZC00YjUxLWE2NzAtMjY0OTA3NTI2NDc2IiwiZXhwIjoxNzUxOTUxMzM3LCJpYXQiOjE3NTEzNDY1Mzd9.seDkG5bcv66SisYPIjmLgQHLxkcYCNXEa6EW7GcxOoQ"
WALLET = "0x87ac324d24a2ee59456321c37c3560a824f375b3"

print("Testing simplified API calls...")

# 1. Test health check
print("\n1. Health Check")
try:
    resp = requests.get(f"{API_BASE_URL}/", timeout=5)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"Error: {e}")

# 2. Test auth verify
print("\n2. Auth Verify")
try:
    resp = requests.post(
        f"{API_BASE_URL}/v1/auth/verify",
        json={"wallet": WALLET, "message": "test", "signature": "test"},
        timeout=5
    )
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"Error: {e}")

# 3. Try the exact same payload format as the extension
print("\n3. Save Message (Extension Format)")
try:
    payload = {
        "message": {
            "id": "msg_test_123",
            "conversation_id": "test_123",
            "session_id": "test_123",
            "role": "user",
            "text": "Test message",
            "timestamp": int(1735689600),  # Unix timestamp for 2025-01-01
            "platform": "claude"
        },
        "conversation_id": "test_123",
        "session_id": "test_123",
        "wallet": WALLET
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    resp = requests.post(
        f"{API_BASE_URL}/v1/conversations/message",
        json=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        },
        timeout=5
    )
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

# 4. Check what the backend expects
print("\n4. Check OpenAPI spec for message endpoint")
try:
    resp = requests.get(f"{API_BASE_URL}/openapi.json", timeout=5)
    if resp.status_code == 200:
        spec = resp.json()
        # Find the message endpoint schema
        message_path = spec.get("paths", {}).get("/v1/conversations/message", {})
        if message_path:
            print("Found endpoint schema")
            post_schema = message_path.get("post", {})
            request_body = post_schema.get("requestBody", {})
            print(f"Request schema: {json.dumps(request_body, indent=2)[:1000]}...")
except Exception as e:
    print(f"Error: {e}")