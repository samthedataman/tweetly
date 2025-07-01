#!/usr/bin/env python3
"""
Test if LanceDB tables are accessible
"""

import os
from dotenv import load_dotenv
import lancedb

# Load environment variables
load_dotenv()

# Configuration
LANCEDB_URI = os.getenv("LANCEDB_URI")
LANCEDB_API_KEY = os.getenv("LANCEDB_API_KEY")

print("🔍 TESTING LANCEDB TABLE ACCESS")
print("=" * 50)

try:
    # Connect to LanceDB
    db = lancedb.connect(
        uri=LANCEDB_URI,
        api_key=LANCEDB_API_KEY,
        region="us-east-1"
    )
    
    print("✅ Connected to LanceDB")
    
    # List tables
    tables = list(db.table_names())
    print(f"📋 Available tables: {tables}")
    
    # Test specific tables
    test_tables = ["users", "sessions", "conversations_v2", "journeys_v2"]
    
    for table_name in test_tables:
        if table_name in tables:
            try:
                table = db.open_table(table_name)
                # For remote LanceDB, we can't use len() directly
                try:
                    df = table.to_pandas()
                    count = len(df) if hasattr(df, '__len__') else df.shape[0]
                    print(f"✅ {table_name}: {count} records")
                except:
                    # Fallback: just check if we can open the table
                    print(f"✅ {table_name}: Table accessible (remote)")
            except Exception as e:
                print(f"❌ {table_name}: Error opening - {e}")
        else:
            print(f"⚠️ {table_name}: Table not found")
            
except Exception as e:
    print(f"❌ Connection error: {e}")
    
print("\n" + "=" * 50)
print("Note: If tables are accessible here but not in the API,")
print("the backend server may need to be restarted to pick up changes.")