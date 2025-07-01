#!/usr/bin/env python3
"""Debug the graph visualization endpoint directly"""

import os
import sys
import traceback
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import lancedb
import jwt

# Add the backend path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'backend', 'api'))

# Import the backend modules
from backend import app, lance_db, graph_embeddings_table, AuthenticatedUser

load_dotenv()

def test_graph_viz_directly():
    """Test the graph visualization function directly"""
    
    print("🔍 DIRECT TEST OF GRAPH VISUALIZATION")
    print("=" * 50)
    
    # Create a mock authenticated user
    test_wallet = "0x742d35cc6634c0532925a3b8d042c18e9c7b8c8d"
    user = AuthenticatedUser(
        user_id=f"test_user_{test_wallet[-8:]}",
        wallet=test_wallet,
        method="wallet",
        session_id="test_session_123",
        total_earnings=0.0
    )
    
    # Test data
    request_data = {"wallet": test_wallet}
    
    try:
        print(f"✅ Testing with user: {user.wallet}")
        print(f"✅ Graph embeddings table available: {graph_embeddings_table is not None}")
        
        if graph_embeddings_table is not None:
            print("✅ Trying to read from graph_embeddings_table...")
            df = graph_embeddings_table.to_pandas()
            print(f"✅ Found {len(df)} entities in graph_embeddings table")
            print(f"✅ Columns: {list(df.columns)}")
            
            if len(df) > 0:
                print(f"✅ Sample data:")
                print(df.head(2))
        else:
            print("❌ graph_embeddings_table is None")
            
        # Try importing and calling the function
        from backend import visualize_knowledge_graph
        
        print("✅ Attempting to call visualization function...")
        
        # Since this is an async function, we need to test it properly
        import asyncio
        
        async def test_call():
            return await visualize_knowledge_graph(request_data, user)
        
        result = asyncio.run(test_call())
        print(f"✅ Result: {result}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"❌ Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    test_graph_viz_directly()