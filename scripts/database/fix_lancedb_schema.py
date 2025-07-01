#!/usr/bin/env python3
"""
Fix LanceDB schemas for Contextly - non-interactive version
"""

import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import lancedb
import pyarrow as pa
import numpy as np

# Load environment variables
load_dotenv()

# Configuration
LANCEDB_URI = os.getenv("LANCEDB_URI")
LANCEDB_API_KEY = os.getenv("LANCEDB_API_KEY")
LANCEDB_REGION = os.getenv("LANCEDB_REGION", "us-east-1")

# Table schemas - copied from init_lancedb.py
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
    
    "conversations_v2": pa.schema([
        ("id", pa.string()),
        ("session_id", pa.string()),
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
    ]),
}

def create_sample_data(table_name: str, schema: pa.Schema) -> pa.Table:
    """Create sample data for testing"""
    
    if table_name == "users":
        data = {
            "_id": ["user_test_1"],
            "wallet": ["0x1234567890abcdef1234567890abcdef12345678"],
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
    
    elif table_name == "conversations_v2":
        data = {
            "id": ["conv_test_1"],
            "session_id": ["session_test_1"],
            "platform": ["claude"],
            "role": ["user"],
            "wallet": ["0x1234567890abcdef1234567890abcdef12345678"],
            "text": ["This is a test conversation"],
            "text_vector": [np.random.randn(1536).astype(np.float32).tolist()],
            "summary_vector": [np.random.randn(384).astype(np.float32).tolist()],
            "timestamp": [int(datetime.utcnow().timestamp())],
            "token_count": [10],
            "has_artifacts": [False],
            "topics": [["test", "initialization"]],
            "entities": ['{"entities": []}'],
            "coherence_score": [0.85],
            "quality_tier": [2],
            "earned_amount": [0.0],
            "contribution_id": [""],
            "blockchain_tx": [""],
        }
    
    elif table_name == "sessions":
        data = {
            "session_id": ["session_test_1"],
            "user_id": ["user_test_1"],
            "wallet": ["0x1234567890abcdef1234567890abcdef12345678"],
            "platform": ["claude"],
            "start_time": [datetime.utcnow().isoformat()],
            "end_time": [""],
            "message_count": [0],
            "total_tokens": [0],
            "ctxt_earned": [0.0],
            "quality_average": [0.0],
            "topics": [[]],
            "is_active": [True],
        }
    
    else:
        raise ValueError(f"Unknown table: {table_name}")
    
    return pa.table(data, schema=schema)

def main():
    """Fix LanceDB schemas"""
    
    print("🔧 FIXING LANCEDB SCHEMAS FOR CONTEXTLY")
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
        
        # Only recreate the critical tables with schema issues
        tables_to_fix = ["users", "sessions", "conversations_v2"]
        
        for table_name in tables_to_fix:
            if table_name in SCHEMAS:
                schema = SCHEMAS[table_name]
                
                print(f"\n🔄 Processing table '{table_name}'...")
                
                # Drop existing table if it exists
                if table_name in existing_tables:
                    print(f"📥 Dropping existing table '{table_name}'")
                    db.drop_table(table_name)
                
                # Create table with proper schema
                print(f"📊 Creating table '{table_name}' with correct schema...")
                sample_data = create_sample_data(table_name, schema)
                table = db.create_table(table_name, sample_data)
                
                print(f"✅ Table '{table_name}' created successfully")
        
        print(f"\n🎉 LanceDB schema fixes complete!")
        print(f"✅ Fixed tables: {tables_to_fix}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()