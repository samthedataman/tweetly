#!/usr/bin/env python3
import requests
import jwt
from datetime import datetime, timedelta, timezone

# Configuration
API_BASE_URL = 'http://localhost:8000'
TEST_WALLET = '0x742d35cc6634c0532925a3b8d042c18e9c7b8c8d'

# Create auth token
payload = {
    'wallet': TEST_WALLET,
    'user_id': f'test_user_{TEST_WALLET[-8:]}',
    'method': 'wallet',
    'session_id': 'test_session_123',
    'total_earnings': 0.0,
    'exp': datetime.now(timezone.utc) + timedelta(hours=24),
    'iat': datetime.now(timezone.utc)
}
JWT_SECRET = 'contextly-secret-key-change-in-production'
auth_token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')

# Test with detailed error info
try:
    response = requests.post(f'{API_BASE_URL}/v1/graph/visualize', 
                           json={'wallet': TEST_WALLET},
                           headers={'Authorization': f'Bearer {auth_token}', 'Content-Type': 'application/json'})
    print(f'Status: {response.status_code}')
    print(f'Headers: {dict(response.headers)}')
    if response.status_code != 200:
        print(f'Error text: {response.text}')
        print(f'Reason: {response.reason}')
    else:
        print(f'Success: {response.json()}')
except Exception as e:
    print(f'Exception: {e}')