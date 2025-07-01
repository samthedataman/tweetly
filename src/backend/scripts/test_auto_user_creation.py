#!/usr/bin/env python3
"""
Test automatic user creation with fixed backend
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

print("🚀 Testing Automatic User Creation")
print(f"Wallet: {WALLET}")
print("="*60)

# 1. First, try to save a message - this should auto-create the user
print("\n💬 1. Saving Test Message (should auto-create user)")
session_id = f"test_{int(time.time())}"

try:
    payload = {
        "message": {
            "id": f"msg_{session_id}_1",
            "conversation_id": session_id,
            "session_id": session_id,
            "role": "user",
            "text": "Hello! Testing automatic user creation.",
            "timestamp": int(time.time()),
            "platform": "claude"
        },
        "conversation_id": session_id,
        "session_id": session_id,
        "wallet": WALLET
    }
    
    print(f"Sending message...")
    resp = requests.post(
        f"{API_BASE_URL}/v1/conversations/message",
        json=payload,
        headers=headers,
        timeout=10
    )
    
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print("✅ Success! Message saved")
        result = resp.json()
        print(f"Response: {json.dumps(result, indent=2)}")
    else:
        print(f"❌ Error: {resp.text}")
        
except Exception as e:
    print(f"❌ Exception: {e}")

# 2. Check if user was created
print("\n" + "="*60)
print("📊 2. Checking User Stats (should now exist)")
try:
    resp = requests.get(
        f"{API_BASE_URL}/v1/stats/{WALLET}",
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=5
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        stats = resp.json()
        print("✅ User found!")
        print(f"Stats: {json.dumps(stats, indent=2)}")
    else:
        print(f"❌ Error: {resp.text}")
except Exception as e:
    print(f"❌ Exception: {e}")

# 3. Save another message to verify it works
print("\n" + "="*60)
print("💬 3. Saving Another Message")
try:
    payload = {
        "message": {
            "id": f"msg_{session_id}_2",
            "conversation_id": session_id,
            "session_id": session_id,
            "role": "assistant",
            "text": "Great! The automatic user creation is working perfectly. Your conversations are now being saved to LanceDB.",
            "timestamp": int(time.time()),
            "platform": "claude"
        },
        "conversation_id": session_id,
        "session_id": session_id,
        "wallet": WALLET
    }
    
    resp = requests.post(
        f"{API_BASE_URL}/v1/conversations/message",
        json=payload,
        headers=headers,
        timeout=10
    )
    
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print("✅ Second message saved successfully!")
    else:
        print(f"❌ Error: {resp.text}")
        
except Exception as e:
    print(f"❌ Exception: {e}")

# 4. List conversations
print("\n" + "="*60)
print("📋 4. Listing Conversations")
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
            print(f"\n- Session: {conv.get('session_id')}")
            print(f"  Platform: {conv.get('platform')}")
            print(f"  Messages: {conv.get('message_count')}")
            print(f"  Created: {conv.get('created_at')}")
    else:
        print(f"❌ Error: {resp.text}")
except Exception as e:
    print(f"❌ Exception: {e}")

print("\n" + "="*60)
print("✅ Test completed!")