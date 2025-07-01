#!/usr/bin/env python3
"""
Test script to send data to the Contextly backend API
"""

import requests
import json
import uuid
from datetime import datetime, timezone, timedelta
# For Python < 3.11 compatibility
UTC = timezone.utc if not hasattr(datetime, 'UTC') else datetime.UTC
import time
import jwt

# Configuration
API_BASE_URL = "http://localhost:8000"
JWT_SECRET = "contextly-secret-key-change-in-production"  # Default from backend

# Generate proper JWT token
def generate_test_token(wallet_address, user_id):
    """Generate a valid JWT token for testing"""
    payload = {
        "wallet": wallet_address,
        "user_id": user_id,
        "exp": datetime.now(UTC) + timedelta(days=7),
        "iat": datetime.now(UTC)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

# Test data
TEST_WALLET = "0x87ac324d24a2ee59456321c37c3560a824f375b3"  # Use the actual wallet from logs
TEST_USER_ID = f"test_user_{TEST_WALLET[-8:]}"
TEST_SESSION_ID = f"test_session_{uuid.uuid4().hex[:8]}"
TEST_CONVERSATION_ID = f"conv_{uuid.uuid4().hex[:8]}"

# Generate valid JWT token
TEST_TOKEN = generate_test_token(TEST_WALLET, TEST_USER_ID)

# Headers with auth token
headers = {
    "Authorization": f"Bearer {TEST_TOKEN}",
    "Content-Type": "application/json",
    "X-Wallet-Address": TEST_WALLET  # Add legacy header as backup
}

def test_user_stats():
    """Test getting user stats"""
    print("\n🔍 Testing GET /v1/stats/{wallet}")
    try:
        response = requests.get(
            f"{API_BASE_URL}/v1/stats/{TEST_WALLET}",
            headers=headers
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_session_history():
    """Test getting session history"""
    print("\n📝 Testing GET /v1/sessions/history")
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/v1/sessions/history",
            headers=headers,
            params={"wallet": TEST_WALLET, "limit": 10}
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"Found {len(data)} sessions")
                if data:
                    print(f"First session: {json.dumps(data[0], indent=2)}")
            else:
                print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_save_conversation():
    """Test saving conversation messages"""
    print("\n💬 Testing POST /v1/conversations/message")
    
    # Save user message
    user_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
    user_message = {
        "message": {
            "id": user_msg_id,
            "conversation_id": TEST_CONVERSATION_ID,
            "session_id": TEST_SESSION_ID,
            "role": "user",
            "text": "Hello, can you help me understand Python decorators?",
            "timestamp": int(time.time()),
            "platform": "claude"
        },
        "conversation_id": TEST_CONVERSATION_ID,
        "session_id": TEST_SESSION_ID,
        "wallet": TEST_WALLET
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/conversations/message",
            headers=headers,
            json=user_message
        )
        print(f"User message - Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        else:
            try:
                print(f"Error response: {json.dumps(response.json(), indent=2)}")
            except:
                print(f"Raw error response: {response.text}")
        
        # Save assistant message
        assistant_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
        assistant_message = {
            "message": {
                "id": assistant_msg_id,
                "conversation_id": TEST_CONVERSATION_ID,
                "session_id": TEST_SESSION_ID,
                "role": "assistant",
                "text": "Of course! Python decorators are a powerful feature that allow you to modify or enhance functions and classes. Let me explain how they work...",
                "timestamp": int(time.time()) + 1,
                "platform": "claude"
            },
            "conversation_id": TEST_CONVERSATION_ID,
            "session_id": TEST_SESSION_ID,
            "wallet": TEST_WALLET
        }
        
        response2 = requests.post(
            f"{API_BASE_URL}/v1/conversations/message",
            headers=headers,
            json=assistant_message
        )
        print(f"\nAssistant message - Status: {response2.status_code}")
        if response2.status_code == 200:
            print(f"Response: {json.dumps(response2.json(), indent=2)}")
        else:
            try:
                print(f"Error response: {json.dumps(response2.json(), indent=2)}")
            except:
                print(f"Raw error response: {response2.text}")
        
        return response.status_code == 200 and response2.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_conversations():
    """Test getting conversation history"""
    print("\n📚 Testing GET /v1/conversations/history")
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/v1/conversations/history",
            headers=headers,
            params={"wallet": TEST_WALLET, "limit": 10}
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"Found {len(data)} conversations")
                if data:
                    print(f"First conversation: {json.dumps(data[0], indent=2)}")
            else:
                print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_earnings():
    """Test getting earnings details"""
    print("\n💰 Testing GET /v1/earnings/details")
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/v1/earnings/details",
            headers=headers,
            params={"wallet": TEST_WALLET}
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_generate_insights():
    """Test generating insights"""
    print("\n📊 Testing POST /v1/insights/generate")
    
    insights_data = {
        "wallet": TEST_WALLET,
        "period": "week"
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/insights/generate",
            headers=headers,
            json=insights_data
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_health_check():
    """Test health check endpoint"""
    print("\n❤️ Testing GET /")
    
    try:
        response = requests.get(f"{API_BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 TESTING CONTEXTLY BACKEND API")
    print("=" * 60)
    print(f"🎯 Target: {API_BASE_URL}")
    print(f"👛 Test Wallet: {TEST_WALLET}")
    print(f"🔑 Test Token: {TEST_TOKEN[:10]}...")
    
    # Check if backend is running
    try:
        response = requests.get(f"{API_BASE_URL}/")
        if response.status_code != 200:
            print("\n❌ Backend is not running! Please start it first.")
            print("Run: cd src/backend && python -m uvicorn api.backend:app --reload")
            return
    except:
        print("\n❌ Cannot connect to backend! Please start it first.")
        print("Run: cd src/backend && python -m uvicorn api.backend:app --reload")
        return
    
    # Run tests
    tests = [
        ("Health Check", test_health_check),
        ("User Stats", test_user_stats),
        ("Session History", test_session_history),
        ("Save Conversation", test_save_conversation),
        ("Get Conversations", test_get_conversations),
        ("Earnings Details", test_earnings),
        ("Generate Insights", test_generate_insights),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        success = test_func()
        results.append((test_name, success))
        time.sleep(0.5)  # Small delay between tests
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:.<40} {status}")
    
    print(f"\n🎯 Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Check the output above.")

if __name__ == "__main__":
    main()