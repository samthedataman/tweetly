#!/usr/bin/env python3
"""
Initialize LanceDB tables for Contextly
Creates all required tables with proper schemas
"""

import os
import sys
import asyncio
from datetime import datetime, timezone
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

# Table schemas
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
        ("role", pa.string()),  # user or assistant
        ("wallet", pa.string()),
        ("text", pa.string()),  # Raw text is stored here
        ("text_vector", pa.list_(pa.float32(), 1536)),  # OpenAI embedding
        ("summary_vector", pa.list_(pa.float32(), 384)),  # MiniLM embedding
        ("timestamp", pa.int64()),
        ("token_count", pa.int64()),
        ("has_artifacts", pa.bool_()),
        ("topics", pa.list_(pa.string())),
        ("entities", pa.string()),  # JSON string
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
    
    "graph_embeddings": pa.schema([
        ("entity_id", pa.string()),
        ("entity_name", pa.string()),
        ("entity_type", pa.string()),
        ("embedding", pa.list_(pa.float32(), 1536)),
        ("community_id", pa.int64()),
        ("centrality_score", pa.float64()),
        ("occurrence_count", pa.int64()),
        ("first_seen", pa.string()),
        ("last_seen", pa.string()),
        ("wallet", pa.string()),
        ("attributes", pa.string()),  # JSON string
    ]),
    
    "journeys_v2": pa.schema([
        ("journey_id", pa.string()),
        ("wallet", pa.string()),
        ("session_id", pa.string()),
        ("timestamp", pa.string()),
        ("platform", pa.string()),
        ("page_type", pa.string()),
        ("action", pa.string()),
        ("duration", pa.int64()),
        ("quality_score", pa.float64()),
        ("ctxt_earned", pa.float64()),
        ("metadata", pa.string()),  # JSON string
    ]),
    
    "summaries": pa.schema([
        ("summary_id", pa.string()),
        ("session_id", pa.string()),
        ("wallet", pa.string()),
        ("summary_text", pa.string()),
        ("summary_vector", pa.list_(pa.float32(), 1536)),
        ("key_points", pa.list_(pa.string())),
        ("action_items", pa.list_(pa.string())),
        ("decisions", pa.list_(pa.string())),
        ("topics", pa.list_(pa.string())),
        ("created_at", pa.string()),
        ("token_count", pa.int64()),
        ("quality_score", pa.float64()),
    ]),
}


def create_sample_data(table_name: str, schema: pa.Schema) -> pa.Table:
    """Create sample data for testing"""
    
    if table_name == "users":
        data = {
            "_id": ["user_test_1"],
            "wallet": ["0x1234567890abcdef1234567890abcdef12345678"],
            "chainId": [8453],
            "created": [datetime.now(timezone.utc).isoformat()],
            "totalEarnings": [0.0],
            "conversationCount": [0],
            "journeyCount": [0],
            "graphNodesCreated": [0],
            "x_username": [""],
            "x_id": [""],
            "auth_method": ["wallet"],
            "last_active": [datetime.now(timezone.utc).isoformat()],
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
            "timestamp": [int(datetime.now(timezone.utc).timestamp())],
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
            "start_time": [datetime.now(timezone.utc).isoformat()],
            "end_time": [""],
            "message_count": [0],
            "total_tokens": [0],
            "ctxt_earned": [0.0],
            "quality_average": [0.0],
            "topics": [[]],
            "is_active": [True],
        }
    
    elif table_name == "graph_embeddings":
        data = {
            "entity_id": ["entity_test_1"],
            "entity_name": ["Test Entity"],
            "entity_type": ["concept"],
            "embedding": [np.random.randn(1536).astype(np.float32).tolist()],
            "community_id": [0],
            "centrality_score": [0.5],
            "occurrence_count": [1],
            "first_seen": [datetime.now(timezone.utc).isoformat()],
            "last_seen": [datetime.now(timezone.utc).isoformat()],
            "wallet": ["0x1234567890abcdef1234567890abcdef12345678"],
            "attributes": ['{"type": "test"}'],
        }
    
    elif table_name == "journeys_v2":
        data = {
            "journey_id": ["journey_test_1"],
            "wallet": ["0x1234567890abcdef1234567890abcdef12345678"],
            "session_id": ["session_test_1"],
            "timestamp": [datetime.now(timezone.utc).isoformat()],
            "platform": ["claude"],
            "page_type": ["conversation"],
            "action": ["start"],
            "duration": [0],
            "quality_score": [0.0],
            "ctxt_earned": [0.0],
            "metadata": ['{}'],
        }
    
    elif table_name == "summaries":
        data = {
            "summary_id": ["summary_test_1"],
            "session_id": ["session_test_1"],
            "wallet": ["0x1234567890abcdef1234567890abcdef12345678"],
            "summary_text": ["Test summary"],
            "summary_vector": [np.random.randn(1536).astype(np.float32).tolist()],
            "key_points": [["Test point"]],
            "action_items": [[]],
            "decisions": [[]],
            "topics": [["test"]],
            "created_at": [datetime.now(timezone.utc).isoformat()],
            "token_count": [10],
            "quality_score": [0.8],
        }
    
    else:
        raise ValueError(f"Unknown table: {table_name}")
    
    return pa.table(data, schema=schema)


async def init_tables():
    """Initialize all LanceDB tables"""
    
    print("🚀 Initializing LanceDB tables for Contextly")
    print(f"URI: {LANCEDB_URI}")
    print(f"Region: {LANCEDB_REGION}")
    print("\n⚠️  This will drop and recreate all tables!")
    
    try:
        # Connect to LanceDB
        db = lancedb.connect(
            uri=LANCEDB_URI,
            api_key=LANCEDB_API_KEY,
            region=LANCEDB_REGION,
        )
        
        print("\n✅ Connected to LanceDB")
        
        # Drop all existing tables first
        existing_tables = list(db.table_names())
        for table_name in SCHEMAS.keys():
            if table_name in existing_tables:
                print(f"📥 Dropping existing table '{table_name}'")
                db.drop_table(table_name)
        
        # Create each table
        for table_name, schema in SCHEMAS.items():
            try:
                # Create table with sample data
                print(f"\n📊 Creating table '{table_name}'...")
                sample_data = create_sample_data(table_name, schema)
                table = db.create_table(table_name, sample_data)
                
                # Create indexes for vector fields
                # Note: Index creation may be skipped in development with minimal data
                try:
                    if table_name == "conversations_v2":
                        # Index for text embeddings
                        table.create_index(
                            metric="cosine",
                            vector_column_name="text_vector",
                            num_partitions=256,
                            num_sub_vectors=96
                        )
                        print(f"  ✅ Created index on text_vector")
                        
                        # Index for summary embeddings
                        table.create_index(
                            metric="cosine",
                            vector_column_name="summary_vector",
                            num_partitions=128,
                            num_sub_vectors=48
                        )
                        print(f"  ✅ Created index on summary_vector")
                    
                    elif table_name == "graph_embeddings":
                        # Index for entity embeddings
                        table.create_index(
                            metric="cosine",
                            vector_column_name="embedding",
                            num_partitions=256,
                            num_sub_vectors=96
                        )
                        print(f"  ✅ Created index on embedding")
                    
                    elif table_name == "summaries":
                        # Index for summary embeddings
                        table.create_index(
                            metric="cosine",
                            vector_column_name="summary_vector",
                            num_partitions=256,
                            num_sub_vectors=96
                        )
                        print(f"  ✅ Created index on summary_vector")
                except Exception as e:
                    if "Not enough rows" in str(e):
                        print(f"  ⚠️  Skipping index creation (not enough sample data for development)")
                    else:
                        print(f"  ⚠️  Error creating index: {e}")
                
                print(f"✅ Table '{table_name}' created successfully")
                
            except Exception as e:
                print(f"❌ Error creating table '{table_name}': {e}")
                continue
        
        # Verify all tables
        print("\n📋 Verifying tables...")
        tables = list(db.table_names())
        print(f"Available tables: {tables}")
        
        # Show table info
        for table_name in SCHEMAS.keys():
            if table_name in tables:
                try:
                    table = db.open_table(table_name)
                    # count_rows() is not supported on LanceDB cloud
                    print(f"  ✅ {table_name}: created")
                except Exception as e:
                    print(f"  ⚠️  {table_name}: {e}")
        
        print("\n🎉 LanceDB initialization complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


def main():
    """Main function"""
    
    # Check environment variables
    if not LANCEDB_URI or not LANCEDB_API_KEY:
        print("❌ Missing required environment variables:")
        print("  - LANCEDB_URI")
        print("  - LANCEDB_API_KEY")
        print("\nPlease set these in your .env file")
        sys.exit(1)
    
    # Run initialization
    asyncio.run(init_tables())


if __name__ == "__main__":
    main()