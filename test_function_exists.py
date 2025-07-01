#!/usr/bin/env python3
"""
Test if backend has loaded the updated functions
"""

import requests
import json

# Simple test to check if backend is working
API_BASE_URL = "http://localhost:8000"

print("Checking if backend is responsive...")
response = requests.get(f"{API_BASE_URL}/")
print(f"Status: {response.status_code}")

if response.status_code == 200:
    print("✅ Backend is running")
    
    # The backend needs to reload to pick up the function rename
    print("\nIf you're still getting 'conversation_delta' errors, the backend needs to reload.")
    print("Even with --reload, sometimes you need to:")
    print("1. Save a trivial change to backend.py (like add/remove a space)")
    print("2. Or restart the backend manually")
else:
    print("❌ Backend is not responding")