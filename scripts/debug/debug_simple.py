#!/usr/bin/env python3
"""Simple debug of graph embeddings table access"""

import os
import sys
from dotenv import load_dotenv
import lancedb

load_dotenv()

# Configuration
LANCEDB_URI = os.getenv("LANCEDB_URI")
LANCEDB_API_KEY = os.getenv("LANCEDB_API_KEY")
LANCEDB_REGION = os.getenv("LANCEDB_REGION", "us-east-1")

def test_table_access():
    """Test direct table access"""
    
    print("🔍 TESTING GRAPH_EMBEDDINGS TABLE ACCESS")
    print("=" * 50)
    
    try:
        # Connect to LanceDB
        db = lancedb.connect(
            uri=LANCEDB_URI,
            api_key=LANCEDB_API_KEY,
            region=LANCEDB_REGION,
        )
        
        print("✅ Connected to LanceDB")
        
        # List tables
        tables = list(db.table_names())
        print(f"✅ Available tables: {tables}")
        
        if "graph_embeddings" in tables:
            print("✅ graph_embeddings table exists")
            
            # Open table
            table = db.open_table("graph_embeddings")
            print("✅ Opened graph_embeddings table")
            
            # Convert to pandas
            try:
                df = table.to_pandas()
                print(f"✅ Converted to pandas - type: {type(df)}")
                
                if hasattr(df, '__len__'):
                    print(f"✅ Length: {len(df)} rows")
                else:
                    print(f"❌ df type {type(df)} has no len() - probably NotImplementedError")
                    print(f"❌ df value: {df}")
                    return
            except Exception as e:
                print(f"❌ to_pandas() failed: {e}")
                return
            
            if len(df) > 0:
                print(f"✅ Columns: {list(df.columns)}")
                print(f"✅ Sample data:")
                for i, row in df.head(3).iterrows():
                    print(f"  Row {i}:")
                    for col in df.columns:
                        val = row[col]
                        if isinstance(val, list) and len(val) > 10:
                            print(f"    {col}: [list of {len(val)} items]")
                        else:
                            print(f"    {col}: {val}")
                    print()
                    
                # Test the .get() access pattern
                print("✅ Testing .get() access pattern:")
                for i, row in df.head(2).iterrows():
                    print(f"  Row {i}:")
                    entity_id = row.get("entity_id", "unknown")
                    entity_name = row.get("entity_name", "Unknown Entity") 
                    community_id = row.get("community_id", 0)
                    print(f"    entity_id: {entity_id}")
                    print(f"    entity_name: {entity_name}")
                    print(f"    community_id: {community_id}")
                    print()
            else:
                print("⚠️ Table is empty")
        else:
            print("❌ graph_embeddings table not found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    test_table_access()