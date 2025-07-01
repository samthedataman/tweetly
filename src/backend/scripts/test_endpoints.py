#!/usr/bin/env python3
"""
Test Contextly API endpoints
"""

import requests
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any
import sys

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_WALLET = "0x1234567890abcdef1234567890abcdef12345678"
TEST_MESSAGE = f"Contextly.ai Authentication\nAddress: {TEST_WALLET}\nTimestamp: {int(time.time())}"
TEST_SIGNATURE = "0xtest_signature_for_testing"  # In real scenario, this would be a proper signature

# Test results
results = {}

def test_endpoint(name: str, method: str, url: str, headers: Dict = None, data: Dict = None, params: Dict = None):
    """Test a single endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Method: {method}")
    print(f"URL: {url}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=10)
        elif method == "POST":
            print(f"Payload: {json.dumps(data, indent=2) if data else 'None'}")
            response = requests.post(url, headers=headers, json=data, timeout=10)
        else:
            response = None
            
        if response:
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}...")  # First 500 chars
            
            results[name] = {
                "status": response.status_code,
                "success": response.status_code < 400,
                "response": response.text[:200]
            }
            
            # Return token if auth endpoint
            if "auth" in url and response.status_code == 200:
                try:
                    return response.json().get("token")
                except:
                    pass
        else:
            results[name] = {"status": "ERROR", "success": False}
            
    except requests.exceptions.Timeout:
        print(f"Error: Request timed out")
        results[name] = {
            "status": "TIMEOUT",
            "success": False,
            "error": "Request timed out after 10 seconds"
        }
    except requests.exceptions.ConnectionError as e:
        print(f"Error: Connection failed - {str(e)}")
        results[name] = {
            "status": "CONNECTION_ERROR",
            "success": False,
            "error": f"Connection error: {str(e)}"
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        results[name] = {
            "status": "ERROR",
            "success": False,
            "error": str(e)
        }
    
    return None

def main():
    print("🚀 Testing Contextly API Endpoints")
    print(f"API Base URL: {API_BASE_URL}")
    
    # Check if server is running
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        print(f"\n✅ Server is running (health check: {response.status_code})")
    except:
        print("\n❌ Server is not running! Please start the backend server.")
        sys.exit(1)
    
    # 1. Test Auth Verify (replaces wallet auth)
    token = test_endpoint(
        "Auth Verify",
        "POST",
        f"{API_BASE_URL}/v1/auth/verify",
        headers={"Content-Type": "application/json"},
        data={
            "wallet": TEST_WALLET,
            "message": TEST_MESSAGE,
            "signature": TEST_SIGNATURE
        }
    )
    
    # Use token for authenticated requests
    auth_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}" if token else "Bearer test_token"
    }
    
    wallet_headers = {
        **auth_headers,
        "X-Wallet-Address": TEST_WALLET
    }
    
    # 2. Test Wallet Registration
    test_endpoint(
        "Wallet Registration",
        "POST",
        f"{API_BASE_URL}/v1/wallet/register",
        headers={"Content-Type": "application/json"},
        data={
            "wallet": TEST_WALLET,
            "signature": TEST_SIGNATURE,
            "message": TEST_MESSAGE,
            "chainId": 1
        }
    )
    
    # 3. Test Twitter Auth Status
    test_endpoint(
        "Twitter Auth Status",
        "GET",
        f"{API_BASE_URL}/v1/auth/x/status",
        headers=auth_headers,
        params={"wallet": TEST_WALLET}
    )
    
    # 4. Test List Conversations (POST endpoint)
    conversation_id = f"test_conv_{int(time.time())}"
    test_endpoint(
        "List Conversations",
        "POST",
        f"{API_BASE_URL}/v1/conversations/list",
        headers=auth_headers,
        data={
            "wallet": TEST_WALLET,
            "limit": 10,
            "offset": 0
        }
    )
    
    # 5. Test Save Message
    test_endpoint(
        "Save Message",
        "POST",
        f"{API_BASE_URL}/v1/conversations/message",
        headers=auth_headers,
        data={
            "message": {
                "id": f"msg_{int(time.time())}_test",
                "conversation_id": conversation_id,
                "session_id": conversation_id,
                "role": "user",
                "text": "This is a test message",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "platform": "claude"
            },
            "conversation_id": conversation_id,
            "session_id": conversation_id,
            "wallet": TEST_WALLET
        }
    )
    
    # 6. Test Conversation History
    test_endpoint(
        "Conversation History",
        "GET",
        f"{API_BASE_URL}/v1/conversations/history",
        headers=auth_headers,
        params={
            "wallet": TEST_WALLET,
            "limit": 10
        }
    )
    
    # 7. Test Session History
    test_endpoint(
        "Session History",
        "GET",
        f"{API_BASE_URL}/v1/sessions/history",
        headers=auth_headers,
        params={
            "wallet": TEST_WALLET,
            "limit": 10
        }
    )
    
    # 8. Test User Stats
    test_endpoint(
        "User Stats",
        "GET",
        f"{API_BASE_URL}/v1/stats/{TEST_WALLET}",
        headers=auth_headers
    )
    
    # 9. Test Earnings Details
    test_endpoint(
        "Earnings Details",
        "GET",
        f"{API_BASE_URL}/v1/earnings/details",
        headers=auth_headers,
        params={"wallet": TEST_WALLET}
    )
    
    # 10. Test Journey Analysis
    test_endpoint(
        "Journey Analysis",
        "POST",
        f"{API_BASE_URL}/v1/journeys/analyze",
        headers=auth_headers,
        data={
            "wallet": TEST_WALLET,
            "journeys": [
                {
                    "pages": [
                        {
                            "url": "https://claude.ai/chat/123",
                            "title": "Test Chat",
                            "duration": 300
                        }
                    ],
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "end_time": datetime.now(timezone.utc).isoformat()
                }
            ]
        }
    )
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for r in results.values() if r["success"])
    failed = total - passed
    
    print(f"\nTotal Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    print("\nDetailed Results:")
    for name, result in results.items():
        status_icon = "✅" if result["success"] else "❌"
        print(f"{status_icon} {name}: {result['status']}")
        if not result["success"] and "error" in result:
            print(f"   Error: {result['error']}")
    
    # Save results to file
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to test_results.json")

if __name__ == "__main__":
    main()