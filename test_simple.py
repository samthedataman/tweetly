#!/usr/bin/env python3
"""
Simple test to check basic API connectivity
"""

import requests
import json

API_BASE_URL = "http://localhost:8000"

def test_root():
    """Test root endpoint"""
    print("Testing GET /")
    response = requests.get(f"{API_BASE_URL}/")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_auth_status():
    """Test auth status endpoint"""
    print("\nTesting GET /v1/auth/x/test")
    response = requests.get(f"{API_BASE_URL}/v1/auth/x/test")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def main():
    print("🧪 SIMPLE API TEST")
    print("=" * 40)
    
    tests = [
        ("Root Endpoint", test_root),
        ("Auth Test", test_auth_status),
    ]
    
    for name, test_func in tests:
        print(f"\n{'='*40}")
        result = test_func()
        print(f"Result: {'✅ PASSED' if result else '❌ FAILED'}")

if __name__ == "__main__":
    main()