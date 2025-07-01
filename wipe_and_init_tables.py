#!/usr/bin/env python3
"""
Wipe all LanceDB tables clean and reinitialize them with proper schemas
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import lancedb
import pyarrow as pa
import numpy as np
import uuid

# Load environment variables
load_dotenv()

# Configuration
LANCEDB_URI = os.getenv("LANCEDB_URI")
LANCEDB_API_KEY = os.getenv("LANCEDB_API_KEY")
LANCEDB_REGION = os.getenv("LANCEDB_REGION", "us-east-1")

# Define all table schemas with ALL required fields
SCHEMAS = {
    "users": pa.schema([
        ("_id", pa.string()),
        ("wallet", pa.string()),
        ("chainId", pa.int64()),
        ("created", pa.string()),
        ("totalEarnings", pa.float64()),
        ("conversationCount", pa.int64()),
        ("journeyCount", pa.int64()),
        ("graphNodesCreated", pa.int64()),
        ("x_username", pa.string()),
        ("x_id", pa.string()),
        ("auth_method", pa.string()),
        ("last_active", pa.string()),
        # Enhanced token tracking fields
        ("total_tokens", pa.int64()),
        ("tokens_by_platform", pa.string()),  # JSON string: {"claude": 1234, "chatgpt": 567}
        ("tokens_by_role", pa.string()),      # JSON string: {"user": 800, "assistant": 1001}
        ("daily_tokens", pa.string()),        # JSON string: {"2025-07-01": 150}
        ("last_token_update", pa.string()),   # ISO timestamp
    ]),
    
    "sessions": pa.schema([
        ("session_id", pa.string()),
        ("user_id", pa.string()),
        ("wallet", pa.string()),
        ("platform", pa.string()),
        ("start_time", pa.string()),
        ("end_time", pa.string()),
        ("message_count", pa.int64()),
        ("total_tokens", pa.int64()),
        ("ctxt_earned", pa.float64()),
        ("quality_average", pa.float64()),
        ("topics", pa.list_(pa.string())),
        ("is_active", pa.bool_()),
        ("last_message", pa.int64()),
        ("allTopics", pa.list_(pa.string())),  # Add for insights endpoint
    ]),
    
    "conversations_v2": pa.schema([
        ("id", pa.string()),
        ("conversation_id", pa.string()),  # ADD THIS - for tracking conversations across sessions
        ("session_id", pa.string()),
        ("user_id", pa.string()),  # Required field that was missing
        ("platform", pa.string()),
        ("role", pa.string()),
        ("wallet", pa.string()),
        ("text", pa.string()),
        ("text_vector", pa.list_(pa.float32(), 1536)),
        ("summary_vector", pa.list_(pa.float32(), 384)),
        ("timestamp", pa.int64()),
        ("token_count", pa.int64()),
        ("token_metrics", pa.string()),      # JSON string with detailed token metrics
        ("has_artifacts", pa.bool_()),
        ("topics", pa.list_(pa.string())),
        ("entities", pa.string()),
        ("coherence_score", pa.float64()),
        ("quality_tier", pa.int64()),
        ("earned_amount", pa.float64()),
        ("contribution_id", pa.string()),
        ("blockchain_tx", pa.string()),
    ]),
    
    "journeys_v2": pa.schema([
        ("_id", pa.string()),
        ("session_id", pa.string()),
        ("wallet", pa.string()),
        ("user_id", pa.string()),
        ("screenshot_ids", pa.list_(pa.string())),
        ("intent", pa.string()),
        ("category", pa.string()),
        ("start_time", pa.int64()),
        ("end_time", pa.int64()),
        ("duration_seconds", pa.int64()),
        ("total_pages", pa.int64()),
        ("unique_domains", pa.int64()),
        ("embedding", pa.list_(pa.float32(), 1536)),
        ("summary", pa.string()),
        ("key_insights", pa.list_(pa.string())),
        ("timestamp", pa.int64()),
    ]),
    
    "graph_embeddings": pa.schema([
        ("entity_id", pa.string()),
        ("entity_name", pa.string()),
        ("entity_type", pa.string()),
        ("embedding", pa.list_(pa.float32(), 384)),
        ("centrality_score", pa.float64()),
        ("community_id", pa.int64()),
        ("timestamp", pa.int64()),
        ("metadata", pa.string()),
    ]),
    
    "graphs": pa.schema([
        ("graph_id", pa.string()),
        ("session_id", pa.string()),
        ("user_id", pa.string()),
        ("wallet", pa.string()),
        ("graph_data", pa.string()),
        ("node_count", pa.int64()),
        ("edge_count", pa.int64()),
        ("density", pa.float64()),
        ("communities", pa.int64()),
        ("timestamp", pa.int64()),
        ("metadata", pa.string()),
    ]),
    
    "summaries": pa.schema([
        ("summary_id", pa.string()),
        ("session_id", pa.string()),
        ("user_id", pa.string()),
        ("wallet", pa.string()),
        ("summary_text", pa.string()),
        ("summary_embedding", pa.list_(pa.float32(), 1536)),
        ("key_points", pa.list_(pa.string())),
        ("topics", pa.list_(pa.string())),
        ("sentiment_score", pa.float64()),
        ("timestamp", pa.int64()),
        ("metadata", pa.string()),
    ]),
    
    "screenshots": pa.schema([
        ("screenshot_id", pa.string()),
        ("journey_id", pa.string()),
        ("user_id", pa.string()),
        ("wallet", pa.string()),
        ("url", pa.string()),
        ("title", pa.string()),
        ("screenshot_data", pa.string()),
        ("embedding", pa.list_(pa.float32(), 1536)),
        ("ocr_text", pa.string()),
        ("timestamp", pa.int64()),
        ("metadata", pa.string()),
    ]),
    
    "artifacts": pa.schema([
        ("artifact_id", pa.string()),
        ("conversation_id", pa.string()),
        ("session_id", pa.string()),
        ("user_id", pa.string()),
        ("wallet", pa.string()),
        ("artifact_type", pa.string()),
        ("content", pa.string()),
        ("language", pa.string()),
        ("embedding", pa.list_(pa.float32(), 1536)),
        ("timestamp", pa.int64()),
        ("metadata", pa.string()),
    ]),
}

def create_initial_data(table_name: str, schema: pa.Schema) -> pa.Table:
    """Create initial data for each table with proper test data"""
    timestamp = int(datetime.utcnow().timestamp())
    test_wallet = "0x742d35cc6634c0532925a3b8d042c18e9c7b8c8d"
    test_user_id = f"test_user_{test_wallet[-8:]}"
    test_session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    
    if table_name == "users":
        # Create a test user
        data = {
            "_id": [test_user_id],
            "wallet": [test_wallet],
            "chainId": [8453],
            "created": [datetime.utcnow().isoformat()],
            "totalEarnings": [100.0],
            "conversationCount": [10],
            "journeyCount": [5],
            "graphNodesCreated": [25],
            "x_username": ["test_user"],
            "x_id": ["123456789"],
            "auth_method": ["wallet"],
            "last_active": [datetime.utcnow().isoformat()],
            # Enhanced token tracking fields
            "total_tokens": [1500],
            "tokens_by_platform": ['{"claude": 800, "chatgpt": 500, "gemini": 200}'],
            "tokens_by_role": ['{"user": 750, "assistant": 750}'],
            "daily_tokens": ['{"2025-07-01": 150, "2025-06-30": 200}'],
            "last_token_update": [datetime.utcnow().isoformat()],
        }
    
    elif table_name == "sessions":
        # Create test sessions
        data = {
            "session_id": [test_session_id, f"test_session_{uuid.uuid4().hex[:8]}"],
            "user_id": [test_user_id, test_user_id],
            "wallet": [test_wallet, test_wallet],
            "platform": ["claude", "chatgpt"],
            "start_time": [datetime.utcnow().isoformat(), datetime.utcnow().isoformat()],
            "end_time": [datetime.utcnow().isoformat(), ""],
            "message_count": [5, 3],
            "total_tokens": [500, 300],
            "ctxt_earned": [10.0, 5.0],
            "quality_average": [0.85, 0.90],
            "topics": [["AI", "coding"], ["data", "analysis"]],
            "is_active": [False, True],
            "last_message": [timestamp - 3600, timestamp],
            "allTopics": [["AI", "coding", "python"], ["data", "analysis", "pandas"]],
        }
    
    elif table_name == "conversations_v2":
        # Create test conversations
        test_conversation_id = f"conv_{uuid.uuid4().hex[:8]}"  # ADD THIS - same conversation_id for both messages
        data = {
            "id": [f"msg_{uuid.uuid4().hex[:8]}", f"msg_{uuid.uuid4().hex[:8]}"],
            "conversation_id": [test_conversation_id, test_conversation_id],  # ADD THIS
            "session_id": [test_session_id, test_session_id],
            "user_id": [test_user_id, test_user_id],
            "platform": ["claude", "claude"],
            "role": ["user", "assistant"],
            "wallet": [test_wallet, test_wallet],
            "text": ["Hello, can you help me with Python?", "Of course! I'd be happy to help you with Python."],
            "text_vector": [np.random.randn(1536).astype(np.float32).tolist(), np.random.randn(1536).astype(np.float32).tolist()],
            "summary_vector": [np.random.randn(384).astype(np.float32).tolist(), np.random.randn(384).astype(np.float32).tolist()],
            "timestamp": [timestamp - 60, timestamp],
            "token_count": [10, 15],
            "token_metrics": [
                '{"total_tokens": 10, "platform": "claude", "encoding_used": "gpt-4", "text_length": 35, "tokens_per_char": 0.29}',
                '{"total_tokens": 15, "platform": "claude", "encoding_used": "gpt-4", "text_length": 48, "tokens_per_char": 0.31}'
            ],
            "has_artifacts": [False, False],
            "topics": [["python", "help"], ["python", "assistance"]],
            "entities": ['{"entities": ["Python"]}', '{"entities": ["Python"]}'],
            "coherence_score": [0.85, 0.90],
            "quality_tier": [3, 3],
            "earned_amount": [1.0, 1.5],
            "contribution_id": ["", ""],
            "blockchain_tx": ["", ""],
        }
    
    elif table_name == "journeys_v2":
        # Create test journey
        data = {
            "_id": [f"journey_{uuid.uuid4().hex[:8]}"],
            "session_id": [test_session_id],
            "wallet": [test_wallet],
            "user_id": [test_user_id],
            "screenshot_ids": [["screenshot_1", "screenshot_2"]],
            "intent": ["learning"],
            "category": ["programming"],
            "start_time": [timestamp - 7200],
            "end_time": [timestamp],
            "duration_seconds": [7200],
            "total_pages": [10],
            "unique_domains": [3],
            "embedding": [np.random.randn(1536).astype(np.float32).tolist()],
            "summary": ["User learning Python programming"],
            "key_insights": [["Python basics", "Data structures", "Functions"]],
            "timestamp": [timestamp],
        }
    
    elif table_name == "graph_embeddings":
        # Create test entities
        entities = ["Python", "Programming", "Data Science", "Machine Learning", "API"]
        data = {
            "entity_id": [f"entity_{uuid.uuid4().hex[:8]}" for _ in entities],
            "entity_name": entities,
            "entity_type": ["language", "concept", "field", "technique", "concept"],
            "embedding": [np.random.randn(384).astype(np.float32).tolist() for _ in entities],
            "centrality_score": [0.9, 0.8, 0.7, 0.6, 0.5],
            "community_id": [1, 1, 2, 2, 1],
            "timestamp": [timestamp] * len(entities),
            "metadata": ['{"source": "test"}'] * len(entities),
        }
    
    elif table_name == "graphs":
        # Create test graph
        data = {
            "graph_id": [f"graph_{uuid.uuid4().hex[:8]}"],
            "session_id": [test_session_id],
            "user_id": [test_user_id],
            "wallet": [test_wallet],
            "graph_data": ['{"nodes": [{"id": "Python", "label": "Python"}], "edges": []}'],
            "node_count": [5],
            "edge_count": [8],
            "density": [0.4],
            "communities": [2],
            "timestamp": [timestamp],
            "metadata": ['{"version": "1.0"}'],
        }
    
    elif table_name == "summaries":
        # Create test summary
        data = {
            "summary_id": [f"summary_{uuid.uuid4().hex[:8]}"],
            "session_id": [test_session_id],
            "user_id": [test_user_id],
            "wallet": [test_wallet],
            "summary_text": ["User discussed Python programming basics and data structures"],
            "summary_embedding": [np.random.randn(1536).astype(np.float32).tolist()],
            "key_points": [["Python syntax", "Lists and dictionaries", "Functions"]],
            "topics": [["Python", "Programming", "Learning"]],
            "sentiment_score": [0.8],
            "timestamp": [timestamp],
            "metadata": ['{"generated_by": "test"}'],
        }
    
    elif table_name == "screenshots":
        # Create test screenshot
        data = {
            "screenshot_id": [f"screenshot_{uuid.uuid4().hex[:8]}"],
            "journey_id": [f"journey_{uuid.uuid4().hex[:8]}"],
            "user_id": [test_user_id],
            "wallet": [test_wallet],
            "url": ["https://python.org"],
            "title": ["Welcome to Python.org"],
            "screenshot_data": ["data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="],
            "embedding": [np.random.randn(1536).astype(np.float32).tolist()],
            "ocr_text": ["Python Programming Language"],
            "timestamp": [timestamp],
            "metadata": ['{"viewport": "1920x1080"}'],
        }
    
    elif table_name == "artifacts":
        # Create test artifact
        data = {
            "artifact_id": [f"artifact_{uuid.uuid4().hex[:8]}"],
            "conversation_id": [f"conv_{uuid.uuid4().hex[:8]}"],
            "session_id": [test_session_id],
            "user_id": [test_user_id],
            "wallet": [test_wallet],
            "artifact_type": ["code"],
            "content": ['print("Hello, World!")'],
            "language": ["python"],
            "embedding": [np.random.randn(1536).astype(np.float32).tolist()],
            "timestamp": [timestamp],
            "metadata": ['{"lines": 1}'],
        }
    
    else:
        raise ValueError(f"Unknown table: {table_name}")
    
    return pa.table(data, schema=schema)

def main():
    """Wipe and reinitialize all tables"""
    
    print("🧹 WIPING AND REINITIALIZING ALL LANCEDB TABLES")
    print("=" * 60)
    print(f"🎯 Target: {LANCEDB_URI}")
    print("⚠️  WARNING: This will DELETE ALL DATA in the tables!")
    
    # Confirm action
    response = input("\nAre you sure you want to wipe all tables? (yes/no): ")
    if response.lower() != "yes":
        print("❌ Operation cancelled")
        return
    
    # Check environment variables
    if not LANCEDB_URI or not LANCEDB_API_KEY:
        print("❌ Missing required environment variables:")
        print("  - LANCEDB_URI")
        print("  - LANCEDB_API_KEY")
        sys.exit(1)
    
    try:
        # Connect to LanceDB
        db = lancedb.connect(
            uri=LANCEDB_URI,
            api_key=LANCEDB_API_KEY,
            region=LANCEDB_REGION,
        )
        
        print("\n✅ Connected to LanceDB")
        
        # Get existing tables
        existing_tables = list(db.table_names())
        print(f"📋 Found {len(existing_tables)} existing tables")
        
        # Drop all tables that we manage
        tables_to_wipe = list(SCHEMAS.keys())
        print(f"\n🗑️  Dropping {len(tables_to_wipe)} tables...")
        
        for table_name in tables_to_wipe:
            if table_name in existing_tables:
                try:
                    db.drop_table(table_name)
                    print(f"  ✅ Dropped table '{table_name}'")
                except Exception as e:
                    print(f"  ⚠️ Failed to drop '{table_name}': {e}")
            else:
                print(f"  ℹ️ Table '{table_name}' doesn't exist")
        
        # Create all tables with initial data
        print(f"\n📊 Creating {len(SCHEMAS)} tables with initial test data...")
        
        for table_name, schema in SCHEMAS.items():
            try:
                initial_data = create_initial_data(table_name, schema)
                db.create_table(table_name, initial_data)
                print(f"  ✅ Created table '{table_name}' with {len(initial_data)} test records")
            except Exception as e:
                print(f"  ❌ Failed to create '{table_name}': {e}")
        
        # Verify all tables are accessible
        print(f"\n🔍 Verifying table access...")
        final_tables = list(db.table_names())
        
        success_count = 0
        for table_name in SCHEMAS.keys():
            if table_name in final_tables:
                try:
                    table = db.open_table(table_name)
                    df = table.to_pandas()
                    record_count = len(df) if hasattr(df, '__len__') else "unknown"
                    print(f"  ✅ {table_name}: Accessible with {record_count} records")
                    success_count += 1
                except Exception as e:
                    print(f"  ⚠️ {table_name}: Accessible but error reading - {e}")
            else:
                print(f"  ❌ {table_name}: Not found")
        
        print(f"\n🎉 Successfully initialized {success_count}/{len(SCHEMAS)} tables!")
        print("\n📝 Test data includes:")
        print(f"  - Test wallet: 0x742d35cc6634c0532925a3b8d042c18e9c7b8c8d")
        print(f"  - Test user ID: test_user_9c7b8c8d")
        print("  - Sample conversations, sessions, and entities")
        print("\n✨ All tables are ready for use!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()