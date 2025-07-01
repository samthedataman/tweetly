#!/usr/bin/env python3
"""Simple test for specific endpoints"""

import requests
import json

base_url = "http://localhost:8000"

print("Testing specific endpoints...")

# Test Save Message endpoint directly
print("\n1. Testing Save Message endpoint...")
try:
    response = requests.post(
        f"{base_url}/v1/conversations/message",
        json={
            "message": {
                "id": "test_msg_123",
                "conversation_id": "test_conv_123",
                "session_id": "test_conv_123",
                "role": "user",
                "text": "Test message",
                "timestamp": "2025-01-01T00:00:00Z",
                "platform": "claude"
            },
            "conversation_id": "test_conv_123",
            "session_id": "test_conv_123",
            "wallet": "0x1234567890abcdef1234567890abcdef12345678"
        },
        timeout=5
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Test stats endpoint
print("\n2. Testing Stats endpoint...")
try:
    response = requests.get(
        f"{base_url}/v1/stats/0x1234567890abcdef1234567890abcdef12345678",
        timeout=5
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Test conversation history
print("\n3. Testing Conversation History...")
try:
    response = requests.get(
        f"{base_url}/v1/conversations/history",
        params={"wallet": "0x1234567890abcdef1234567890abcdef12345678"},
        timeout=5
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")