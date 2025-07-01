#!/usr/bin/env python3
"""
Direct test to trigger the error and see what happens
"""

import os
import sys
sys.path.insert(0, '/Users/samsavage/contextly/contextly/src/backend')

# Set environment variables
os.environ['LANCEDB_URI'] = os.getenv('LANCEDB_URI', 'db://contextly-ynuhzo')
os.environ['LANCEDB_API_KEY'] = os.getenv('LANCEDB_API_KEY', '')

try:
    from api.backend import safe_table_to_pandas, db
    
    print("Testing safe_table_to_pandas function...")
    
    # Test the users table
    if db and hasattr(db, 'open_table'):
        try:
            users_table = db.open_table("users")
            print("✅ Opened users table")
            
            # Test safe wrapper
            result = safe_table_to_pandas(users_table, "users")
            if result is None:
                print("✅ safe_table_to_pandas returned None (expected for remote LanceDB)")
            else:
                print(f"✅ safe_table_to_pandas returned DataFrame with {len(result)} rows")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print("❌ Database not initialized")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the contextly directory")