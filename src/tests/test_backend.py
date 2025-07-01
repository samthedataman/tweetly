#!/usr/bin/env python3
"""
Test the enhanced backend API
"""

import asyncio
import httpx
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

async def test_api():
    async with httpx.AsyncClient() as client:
        # Test home endpoint
        print("Testing home endpoint...")
        response = await client.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}\n")
        
        # Test wallet registration
        print("Testing wallet registration...")
        wallet_data = {
            "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f6b123",
            "signature": "0x1234567890abcdef",  # Mock signature
            "message": "Sign this message to authenticate",
            "chainId": 1
        }
        
        try:
            response = await client.post(f"{BASE_URL}/v1/wallet/register", json=wallet_data)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print(f"Response: {json.dumps(response.json(), indent=2)}\n")
        except Exception as e:
            print(f"Error: {e}\n")
        
        # Test summarization endpoint
        print("Testing summarization endpoint...")
        summarize_data = {
            "session_id": "test-session-123",
            "messages": [
                {
                    "id": "msg1",
                    "session_id": "test-session-123",
                    "role": "user",
                    "text": "Can you explain what GraphRAG is and how it works?",
                    "timestamp": int(datetime.now().timestamp()),
                    "platform": "claude"
                },
                {
                    "id": "msg2",
                    "session_id": "test-session-123",
                    "role": "assistant",
                    "text": "GraphRAG (Graph-based Retrieval Augmented Generation) is an advanced technique that combines knowledge graphs with RAG to improve information retrieval and generation. It works by extracting entities and relationships from text to build a graph structure, then using this graph to provide better context for LLM queries.",
                    "timestamp": int(datetime.now().timestamp()),
                    "platform": "claude"
                }
            ],
            "mode": "brief"
        }
        
        try:
            response = await client.post(f"{BASE_URL}/v1/conversations/summarize", json=summarize_data)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print(f"Response: {json.dumps(response.json(), indent=2)}\n")
        except Exception as e:
            print(f"Error: {e}\n")
        
        # Test title generation
        print("Testing title generation...")
        title_data = {
            "session_id": "test-session-123",
            "messages": summarize_data["messages"],
            "style": "descriptive",
            "include_emoji": True
        }
        
        try:
            response = await client.post(f"{BASE_URL}/v1/conversations/title", json=title_data)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print(f"Response: {json.dumps(response.json(), indent=2)}\n")
        except Exception as e:
            print(f"Error: {e}\n")

if __name__ == "__main__":
    print("""
    🧪 Testing Contextly Enhanced Backend
    =====================================
    
    This will test the main endpoints of the enhanced backend.
    Make sure the backend is running on port 8000.
    
    """)
    
    asyncio.run(test_api())