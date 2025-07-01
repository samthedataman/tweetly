#!/usr/bin/env python3
"""
Ensure all required LanceDB tables exist with proper schemas
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

# Define all table schemas
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
        ("last_message", pa.int64()),  # Add timestamp for filtering
    ]),
    
    "conversations_v2": pa.schema([
        ("id", pa.string()),
        ("session_id", pa.string()),
        ("user_id", pa.string()),  # Add missing user_id field
        ("platform", pa.string()),
        ("role", pa.string()),
        ("wallet", pa.string()),
        ("text", pa.string()),
        ("text_vector", pa.list_(pa.float32(), 1536)),
        ("summary_vector", pa.list_(pa.float32(), 384)),
        ("timestamp", pa.int64()),
        ("token_count", pa.int64()),
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
        ("graph_data", pa.string()),  # JSON serialized networkx graph
        ("node_count", pa.int64()),
        ("edge_count", pa.int64()),
        ("density", pa.float64()),
        ("communities", pa.int64()),
        ("timestamp", pa.int64()),
        ("metadata", pa.string()),
    ]),
}

def create_sample_data(table_name: str, schema: pa.Schema) -> pa.Table:
    """Create sample data for each table"""
    timestamp = int(datetime.utcnow().timestamp())
    
    if table_name == "users":
        data = {
            "_id": [f"user_{uuid.uuid4().hex[:8]}"],
            "wallet": ["0x0000000000000000000000000000000000000000"],
            "chainId": [8453],
            "created": [datetime.utcnow().isoformat()],
            "totalEarnings": [0.0],
            "conversationCount": [0],
            "journeyCount": [0],
            "graphNodesCreated": [0],
            "x_username": [""],
            "x_id": [""],
            "auth_method": ["wallet"],
            "last_active": [datetime.utcnow().isoformat()],
        }
    
    elif table_name == "sessions":
        data = {
            "session_id": [f"session_{uuid.uuid4().hex[:8]}"],
            "user_id": [f"user_{uuid.uuid4().hex[:8]}"],
            "wallet": ["0x0000000000000000000000000000000000000000"],
            "platform": ["claude"],
            "start_time": [datetime.utcnow().isoformat()],
            "end_time": [""],
            "message_count": [0],
            "total_tokens": [0],
            "ctxt_earned": [0.0],
            "quality_average": [0.0],
            "topics": [[]],
            "is_active": [True],
            "last_message": [timestamp],
        }
    
    elif table_name == "conversations_v2":
        data = {
            "id": [f"conv_{uuid.uuid4().hex[:8]}"],
            "session_id": [f"session_{uuid.uuid4().hex[:8]}"],
            "user_id": [f"user_{uuid.uuid4().hex[:8]}"],
            "platform": ["claude"],
            "role": ["user"],
            "wallet": ["0x0000000000000000000000000000000000000000"],
            "text": ["Initial message"],
            "text_vector": [np.random.randn(1536).astype(np.float32).tolist()],
            "summary_vector": [np.random.randn(384).astype(np.float32).tolist()],
            "timestamp": [timestamp],
            "token_count": [5],
            "has_artifacts": [False],
            "topics": [["initialization"]],
            "entities": ['{"entities": []}'],
            "coherence_score": [0.85],
            "quality_tier": [2],
            "earned_amount": [0.0],
            "contribution_id": [""],
            "blockchain_tx": [""],
        }
    
    elif table_name == "journeys_v2":
        data = {
            "_id": [f"journey_{uuid.uuid4().hex[:8]}"],
            "session_id": [f"session_{uuid.uuid4().hex[:8]}"],
            "wallet": ["0x0000000000000000000000000000000000000000"],
            "user_id": [f"user_{uuid.uuid4().hex[:8]}"],
            "screenshot_ids": [[]],
            "intent": ["exploration"],
            "category": ["general"],
            "start_time": [timestamp],
            "end_time": [timestamp],
            "duration_seconds": [0],
            "total_pages": [1],
            "unique_domains": [1],
            "embedding": [np.random.randn(1536).astype(np.float32).tolist()],
            "summary": ["Initial journey"],
            "key_insights": [[]],
            "timestamp": [timestamp],
        }
    
    elif table_name == "graph_embeddings":
        data = {
            "entity_id": [f"entity_{uuid.uuid4().hex[:8]}"],
            "entity_name": ["Initial Entity"],
            "entity_type": ["concept"],
            "embedding": [np.random.randn(384).astype(np.float32).tolist()],
            "centrality_score": [0.5],
            "community_id": [0],
            "timestamp": [timestamp],
            "metadata": ['{}'],
        }
    
    elif table_name == "graphs":
        data = {
            "graph_id": [f"graph_{uuid.uuid4().hex[:8]}"],
            "session_id": [f"session_{uuid.uuid4().hex[:8]}"],
            "user_id": [f"user_{uuid.uuid4().hex[:8]}"],
            "wallet": ["0x0000000000000000000000000000000000000000"],
            "graph_data": ['{"nodes": [], "edges": []}'],
            "node_count": [0],
            "edge_count": [0],
            "density": [0.0],
            "communities": [0],
            "timestamp": [timestamp],
            "metadata": ['{}'],
        }
    
    else:
        raise ValueError(f"Unknown table: {table_name}")
    
    return pa.table(data, schema=schema)

def main():
    """Ensure all tables exist"""
    
    print("🔧 ENSURING ALL LANCEDB TABLES EXIST")
    print("=" * 60)
    print(f"🎯 Target: {LANCEDB_URI}")
    
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
        
        print("✅ Connected to LanceDB")
        
        # Get existing tables
        existing_tables = list(db.table_names())
        print(f"📋 Existing tables: {existing_tables}")
        
        # Create missing tables
        for table_name, schema in SCHEMAS.items():
            if table_name not in existing_tables:
                print(f"\n📊 Creating missing table '{table_name}'...")
                sample_data = create_sample_data(table_name, schema)
                db.create_table(table_name, sample_data)
                print(f"✅ Created table '{table_name}'")
            else:
                print(f"✓ Table '{table_name}' already exists")
        
        # Verify all tables are accessible
        print(f"\n🔍 Verifying table access...")
        final_tables = list(db.table_names())
        
        for table_name in SCHEMAS.keys():
            if table_name in final_tables:
                try:
                    table = db.open_table(table_name)
                    # Try to access it
                    _ = table.to_pandas()
                    print(f"✅ {table_name}: Accessible")
                except Exception as e:
                    print(f"⚠️ {table_name}: Accessible but error reading data - {e}")
            else:
                print(f"❌ {table_name}: Not found")
        
        print(f"\n🎉 All required tables are ensured!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()