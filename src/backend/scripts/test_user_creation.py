#!/usr/bin/env python3
"""
Test user creation and then save messages
"""

import requests
import json
import time

API_BASE_URL = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ3YWxsZXQiOiIweDg3YWMzMjRkMjRhMmVlNTk0NTYzMjFjMzdjMzU2MGE4MjRmMzc1YjMiLCJ1c2VyX2lkIjoiMDNiY2I2ZDMtOTVhZC00YjUxLWE2NzAtMjY0OTA3NTI2NDc2IiwiZXhwIjoxNzUxOTUxMzM3LCJpYXQiOjE3NTEzNDY1Mzd9.seDkG5bcv66SisYPIjmLgQHLxkcYCNXEa6EW7GcxOoQ"
WALLET = "0x87ac324d24a2ee59456321c37c3560a824f375b3"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "X-Wallet-Address": WALLET
}

print("Testing user creation flow...")

# 1. Try wallet registration (this might create the user)
print("\n1. Wallet Registration")
try:
    # Generate a test message and signature
    timestamp = int(time.time())
    message = f"Contextly.ai Authentication\nAddress: {WALLET}\nTimestamp: {timestamp}"
    
    resp = requests.post(
        f"{API_BASE_URL}/v1/wallet/register",
        json={
            "wallet": WALLET,
            "message": message,
            "signature": "0xtest_signature",  # Invalid but might create user
            "chainId": 1
        },
        timeout=5
    )
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:200]}")
except Exception as e:
    print(f"Error: {e}")

# 2. Check if we can access the user stats now
print("\n2. Check User Stats (with auth)")
try:
    resp = requests.get(
        f"{API_BASE_URL}/v1/stats/{WALLET}",
        headers=headers,
        timeout=5
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print(f"User found! Stats: {resp.json()}")
    else:
        print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")

# 3. Try a minimal message save
print("\n3. Save Minimal Message")
try:
    session_id = f"test_{int(time.time())}"
    payload = {
        "message": {
            "id": f"msg_{session_id}_1",
            "conversation_id": session_id,
            "session_id": session_id,
            "role": "user",
            "text": "Hello, this is a test",
            "timestamp": int(time.time()),
            "platform": "claude"
        },
        "conversation_id": session_id,
        "session_id": session_id,
        "wallet": WALLET
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    resp = requests.post(
        f"{API_BASE_URL}/v1/conversations/message",
        json=payload,
        headers=headers,
        timeout=5
    )
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")
    
    if resp.status_code == 200:
        print("\n✅ Success! Message saved")
        result = resp.json()
        print(f"Result: {json.dumps(result, indent=2)}")
except Exception as e:
    print(f"Error: {e}")

# 4. List conversations to verify
print("\n4. List Conversations")
try:
    resp = requests.post(
        f"{API_BASE_URL}/v1/conversations/list",
        json={"wallet": WALLET, "limit": 5, "offset": 0},
        headers=headers,
        timeout=5
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Total conversations: {data.get('total', 0)}")
        for conv in data.get('conversations', []):
            print(f"- {conv.get('session_id')} ({conv.get('message_count')} messages)")
except Exception as e:
    print(f"Error: {e}")