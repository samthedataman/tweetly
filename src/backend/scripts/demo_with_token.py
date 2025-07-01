#!/usr/bin/env python3
"""
Demo script to test Contextly API with real authentication token
"""

import requests
import json
import time
from datetime import datetime, timezone
import sys

# Configuration
API_BASE_URL = "http://localhost:8000"

def run_demo(token, wallet_address):
    """Run demo with provided token"""
    
    print("🚀 Running Contextly API Demo")
    print(f"API: {API_BASE_URL}")
    print(f"Wallet: {wallet_address}")
    print(f"Token: {token[:20]}...")
    
    # Headers for authenticated requests
    auth_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "X-Wallet-Address": wallet_address
    }
    
    # 1. Check user stats
    print("\n" + "="*60)
    print("📊 1. Checking User Stats")
    try:
        response = requests.get(
            f"{API_BASE_URL}/v1/stats/{wallet_address}",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            stats = response.json()
            print(f"Conversations: {stats.get('conversationCount', 0)}")
            print(f"Total Earnings: {stats.get('totalEarnings', 0)}")
            print(f"Day Streak: {stats.get('dayStreak', 0)}")
        else:
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # 2. Save a test conversation with multiple messages
    print("\n" + "="*60)
    print("💬 2. Saving Test Conversation")
    
    session_id = f"demo_{int(time.time())}"
    
    # First, create conversation metadata
    messages = [
        {
            "role": "user",
            "text": "What is the best way to implement a REST API in Python?",
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        {
            "role": "assistant",
            "text": "The best way to implement a REST API in Python is using FastAPI. It provides automatic validation, serialization, and documentation.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        {
            "role": "user",
            "text": "Can you show me a simple example?",
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        {
            "role": "assistant",
            "text": "Here's a simple FastAPI example:\n\n```python\nfrom fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/hello')\ndef hello():\n    return {'message': 'Hello World!'}\n```",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    # Save each message
    saved_count = 0
    for i, msg in enumerate(messages):
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
                    "wallet": wallet_address
                }
            )
            if response.status_code == 200:
                saved_count += 1
                print(f"✅ Saved message {i+1}/{len(messages)}")
            else:
                print(f"❌ Failed to save message {i+1}: {response.text}")
        except Exception as e:
            print(f"❌ Error saving message {i+1}: {e}")
    
    print(f"\nTotal messages saved: {saved_count}/{len(messages)}")
    
    # 3. List conversations
    print("\n" + "="*60)
    print("📋 3. Listing Conversations")
    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/conversations/list",
            headers=auth_headers,
            json={
                "wallet": wallet_address,
                "limit": 5,
                "offset": 0
            }
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Total conversations: {data.get('total', 0)}")
            for conv in data.get('conversations', [])[:3]:  # Show first 3
                print(f"\n- Session: {conv.get('session_id', 'N/A')}")
                print(f"  Messages: {conv.get('message_count', 0)}")
                print(f"  Platform: {conv.get('platform', 'N/A')}")
        else:
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # 4. Get conversation history
    print("\n" + "="*60)
    print("📜 4. Getting Conversation History")
    try:
        response = requests.get(
            f"{API_BASE_URL}/v1/conversations/history",
            headers=auth_headers,
            params={"wallet": wallet_address, "limit": 5}
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            history = response.json()
            print(f"Found {len(history.get('conversations', []))} conversations")
        else:
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # 5. Analyze journey data
    print("\n" + "="*60)
    print("🗺️ 5. Analyzing Journey Data")
    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/journeys/analyze",
            headers=auth_headers,
            json={
                "wallet": wallet_address,
                "journeys": [
                    {
                        "pages": [
                            {
                                "url": "https://claude.ai/chat/123",
                                "title": "Python API Discussion",
                                "duration": 300
                            },
                            {
                                "url": "https://claude.ai/chat/456",
                                "title": "FastAPI Tutorial",
                                "duration": 600
                            }
                        ],
                        "start_time": datetime.now(timezone.utc).isoformat(),
                        "end_time": datetime.now(timezone.utc).isoformat()
                    }
                ]
            }
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Journey analysis completed")
        else:
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # 6. Get earnings details
    print("\n" + "="*60)
    print("💰 6. Getting Earnings Details")
    try:
        response = requests.get(
            f"{API_BASE_URL}/v1/earnings/details",
            headers=auth_headers,
            params={"wallet": wallet_address}
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            earnings = response.json()
            print(f"Total earnings: {earnings.get('total_earnings', 0)} CTXT")
        else:
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*60)
    print("✅ Demo completed!")

def main():
    """Main function"""
    print("Contextly API Demo with Authentication")
    print("="*60)
    
    # Get token from user
    token = input("\nPlease enter your authentication token: ").strip()
    if not token:
        print("❌ No token provided")
        sys.exit(1)
    
    # Get wallet address
    wallet = input("Please enter your wallet address: ").strip()
    if not wallet:
        print("❌ No wallet address provided")
        sys.exit(1)
    
    # Run the demo
    run_demo(token, wallet)

if __name__ == "__main__":
    main()