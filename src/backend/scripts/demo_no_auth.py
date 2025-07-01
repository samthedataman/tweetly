#!/usr/bin/env python3
"""
Demo script to test Contextly API without authentication
Tests public endpoints and shows API structure
"""

import requests
import json
import time
from datetime import datetime, timezone

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_WALLET = "0x1234567890abcdef1234567890abcdef12345678"

def test_public_endpoints():
    """Test endpoints that don't require authentication"""
    
    print("🚀 Testing Contextly Public API Endpoints")
    print(f"API: {API_BASE_URL}")
    print("="*60)
    
    # 1. Health Check
    print("\n📡 1. API Health Check")
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Service: {data.get('service')}")
            print(f"Version: {data.get('version')}")
            print(f"Status: {data.get('status')}")
            print("Features:")
            for feature, desc in data.get('features', {}).items():
                print(f"  - {feature}: {desc}")
    except Exception as e:
        print(f"Error: {e}")
    
    # 2. Check Auth Verify (without valid signature)
    print("\n" + "="*60)
    print("🔐 2. Auth Verify Endpoint (testing structure)")
    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/auth/verify",
            json={
                "wallet": TEST_WALLET,
                "message": "Test message",
                "signature": "0xtest_signature"
            },
            timeout=5
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print("Note: Returns false as signature is invalid (expected)")
    except Exception as e:
        print(f"Error: {e}")
    
    # 3. Twitter/X Auth Status (no wallet required for structure)
    print("\n" + "="*60)
    print("🐦 3. Twitter/X Auth Status")
    try:
        response = requests.get(
            f"{API_BASE_URL}/v1/auth/x/status",
            params={"wallet": TEST_WALLET},
            timeout=5
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    # 4. Test endpoints that require auth (to show structure)
    print("\n" + "="*60)
    print("📝 4. Protected Endpoints (showing required auth)")
    
    protected_endpoints = [
        ("POST", "/v1/conversations/message", "Save Message"),
        ("GET", f"/v1/stats/{TEST_WALLET}", "User Stats"),
        ("GET", "/v1/conversations/history", "Conversation History"),
        ("POST", "/v1/conversations/list", "List Conversations"),
        ("GET", "/v1/earnings/details", "Earnings Details")
    ]
    
    for method, endpoint, name in protected_endpoints:
        print(f"\n• {name} ({method} {endpoint})")
        try:
            if method == "GET":
                response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=5)
            else:
                response = requests.post(f"{API_BASE_URL}{endpoint}", json={}, timeout=5)
            
            print(f"  Status: {response.status_code}")
            if response.status_code == 401:
                print(f"  Auth Required: {response.json().get('detail', 'Authentication required')}")
            else:
                print(f"  Response: {response.text[:100]}...")
        except Exception as e:
            print(f"  Error: {e}")
    
    # 5. Show authentication flow
    print("\n" + "="*60)
    print("🔑 5. Authentication Flow (for reference)")
    print("\n1. User signs message with wallet")
    print("2. POST /v1/wallet/register with:")
    print("   - wallet: user's wallet address")
    print("   - message: signed message")
    print("   - signature: wallet signature")
    print("   - chainId: blockchain chain ID")
    print("3. Backend returns JWT token")
    print("4. Include token in subsequent requests:")
    print("   - Header: Authorization: Bearer <token>")
    print("   - Header: X-Wallet-Address: <wallet>")
    
    # 6. Show data structure examples
    print("\n" + "="*60)
    print("📦 6. Data Structure Examples")
    
    print("\nMessage Structure:")
    print(json.dumps({
        "message": {
            "id": "msg_123",
            "conversation_id": "conv_123",
            "session_id": "session_123",
            "role": "user|assistant",
            "text": "message content",
            "timestamp": "2025-01-01T00:00:00Z",
            "platform": "claude|chatgpt|gemini"
        },
        "wallet": "0x..."
    }, indent=2))
    
    print("\nConversation List Request:")
    print(json.dumps({
        "wallet": "0x...",
        "limit": 10,
        "offset": 0
    }, indent=2))
    
    print("\nJourney Analysis Request:")
    print(json.dumps({
        "wallet": "0x...",
        "journeys": [{
            "pages": [{
                "url": "https://claude.ai/chat/123",
                "title": "Chat Title",
                "duration": 300
            }],
            "start_time": "2025-01-01T00:00:00Z",
            "end_time": "2025-01-01T00:05:00Z"
        }]
    }, indent=2))

def create_mock_wallet_auth():
    """Show how to create wallet authentication"""
    print("\n" + "="*60)
    print("🔐 Mock Wallet Authentication Demo")
    print("="*60)
    
    # In a real scenario, this would use web3.py or ethers.js
    print("\nIn the browser extension, authentication works like this:")
    print("\n1. Generate message to sign:")
    timestamp = int(time.time())
    message = f"Contextly.ai Authentication\nAddress: {TEST_WALLET}\nTimestamp: {timestamp}"
    print(f"   {message}")
    
    print("\n2. User signs with wallet (MetaMask, etc.)")
    print("   const signature = await ethereum.request({")
    print("     method: 'personal_sign',")
    print("     params: [message, walletAddress]")
    print("   });")
    
    print("\n3. Send to backend:")
    print("   POST /v1/wallet/register")
    print("   {")
    print(f'     "wallet": "{TEST_WALLET}",')
    print(f'     "message": "{message}",')
    print('     "signature": "0x...",')
    print('     "chainId": 1')
    print("   }")
    
    print("\n4. Backend verifies signature and returns JWT token")
    print("5. Use token for all authenticated requests")

def main():
    """Main function"""
    print("\n🎯 Contextly API Demo (No Authentication Required)")
    print("This demo shows API structure and public endpoints\n")
    
    # Check if server is running
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=2)
        if response.status_code != 200:
            print("⚠️  Backend server returned unexpected status")
    except:
        print("❌ Backend server is not running!")
        print(f"Please start the server at {API_BASE_URL}")
        return
    
    # Run tests
    test_public_endpoints()
    create_mock_wallet_auth()
    
    print("\n" + "="*60)
    print("✅ Demo completed!")
    print("\nTo test authenticated endpoints:")
    print("1. Run the browser extension and sign in with wallet")
    print("2. Capture the JWT token from browser DevTools")
    print("3. Use demo_with_token.py with the captured token")

if __name__ == "__main__":
    main()