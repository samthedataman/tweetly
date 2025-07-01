#!/usr/bin/env python3
"""
Test Contextly API with real authentication token
"""

import requests
import json
import time
from datetime import datetime, timezone

# Configuration
API_BASE_URL = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ3YWxsZXQiOiIweDg3YWMzMjRkMjRhMmVlNTk0NTYzMjFjMzdjMzU2MGE4MjRmMzc1YjMiLCJ1c2VyX2lkIjoiMDNiY2I2ZDMtOTVhZC00YjUxLWE2NzAtMjY0OTA3NTI2NDc2IiwiZXhwIjoxNzUxOTUxMzM3LCJpYXQiOjE3NTEzNDY1Mzd9.seDkG5bcv66SisYPIjmLgQHLxkcYCNXEa6EW7GcxOoQ"
WALLET_ADDRESS = "0x87ac324d24a2ee59456321c37c3560a824f375b3"

# Headers for authenticated requests
auth_headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TOKEN}",
    "X-Wallet-Address": WALLET_ADDRESS
}

print("🚀 Testing Contextly API with Real Token")
print(f"API: {API_BASE_URL}")
print(f"Wallet: {WALLET_ADDRESS}")
print(f"Token: {TOKEN[:40]}...")
print("="*60)

# 1. Check user stats
print("\n📊 1. Checking User Stats")
try:
    response = requests.get(
        f"{API_BASE_URL}/v1/stats/{WALLET_ADDRESS}",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        stats = response.json()
        print(f"Response: {json.dumps(stats, indent=2)}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# 2. List existing conversations
print("\n" + "="*60)
print("📋 2. Listing Existing Conversations")
try:
    response = requests.post(
        f"{API_BASE_URL}/v1/conversations/list",
        headers=auth_headers,
        json={
            "wallet": WALLET_ADDRESS,
            "limit": 5,
            "offset": 0
        }
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Total conversations: {data.get('total', 0)}")
        print(f"Conversations returned: {len(data.get('conversations', []))}")
        for conv in data.get('conversations', [])[:3]:
            print(f"\n- Session: {conv.get('session_id', 'N/A')}")
            print(f"  Platform: {conv.get('platform', 'N/A')}")
            print(f"  Messages: {conv.get('message_count', 0)}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# 3. Save a test conversation
print("\n" + "="*60)
print("💬 3. Saving Test Conversation")

session_id = f"test_session_{int(time.time())}"

# Save messages one by one (like the extension does)
test_messages = [
    {
        "role": "user",
        "text": "What is the best way to implement authentication in a Chrome extension?",
        "timestamp": int(datetime.now(timezone.utc).timestamp())
    },
    {
        "role": "assistant",
        "text": "The best way to implement authentication in a Chrome extension involves several approaches:\n\n1. **OAuth 2.0 Flow**: Use chrome.identity API for OAuth authentication with services like Google, GitHub, etc.\n\n2. **Custom Backend Auth**: Implement your own authentication server and use tokens stored in chrome.storage.\n\n3. **Wallet-based Auth**: For Web3 apps, use wallet signatures for authentication.\n\nHere's a simple example using chrome.identity:\n\n```javascript\nchrome.identity.getAuthToken({ interactive: true }, function(token) {\n  if (chrome.runtime.lastError) {\n    console.error(chrome.runtime.lastError);\n    return;\n  }\n  // Use the token for API requests\n  console.log('Auth token:', token);\n});\n```",
        "timestamp": int(datetime.now(timezone.utc).timestamp())
    }
]

saved_count = 0
for i, msg in enumerate(test_messages):
    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/conversations/message",
            headers=auth_headers,
            json={
                "message": {
                    "id": f"msg_{session_id}_{i}",
                    "conversation_id": session_id,
                    "session_id": session_id,
                    "role": msg["role"],
                    "text": msg["text"],
                    "timestamp": msg["timestamp"],
                    "platform": "claude"
                },
                "conversation_id": session_id,
                "session_id": session_id,
                "wallet": WALLET_ADDRESS
            }
        )
        print(f"\nMessage {i+1}: {msg['role'][:20]}...")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            saved_count += 1
            result = response.json()
            print(f"✅ Saved successfully")
            print(f"Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ Failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

print(f"\nTotal messages saved: {saved_count}/{len(test_messages)}")

# 4. Verify the conversation was saved
print("\n" + "="*60)
print("🔍 4. Verifying Saved Conversation")
time.sleep(1)  # Give it a moment to process

try:
    response = requests.post(
        f"{API_BASE_URL}/v1/conversations/list",
        headers=auth_headers,
        json={
            "wallet": WALLET_ADDRESS,
            "limit": 1,
            "offset": 0
        }
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Total conversations now: {data.get('total', 0)}")
        latest = data.get('conversations', [])[0] if data.get('conversations') else None
        if latest:
            print(f"\nLatest conversation:")
            print(f"- Session ID: {latest.get('session_id')}")
            print(f"- Created: {latest.get('created_at')}")
            print(f"- Messages: {latest.get('message_count')}")
            print(f"- Platform: {latest.get('platform')}")
except Exception as e:
    print(f"Error: {e}")

# 5. Get conversation history
print("\n" + "="*60)
print("📜 5. Getting Conversation History")
try:
    response = requests.get(
        f"{API_BASE_URL}/v1/conversations/history",
        headers=auth_headers,
        params={"wallet": WALLET_ADDRESS, "limit": 5}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        history = response.json()
        print(f"Response: {json.dumps(history, indent=2)}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# 6. Test earnings endpoint
print("\n" + "="*60)
print("💰 6. Getting Earnings Details")
try:
    response = requests.get(
        f"{API_BASE_URL}/v1/earnings/details",
        headers=auth_headers,
        params={"wallet": WALLET_ADDRESS}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        earnings = response.json()
        print(f"Response: {json.dumps(earnings, indent=2)}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*60)
print("✅ Test completed!")