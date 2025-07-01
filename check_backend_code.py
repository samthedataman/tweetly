#!/usr/bin/env python3
"""
Check if backend has the updated code
"""

import os

backend_file = "/Users/samsavage/contextly/contextly/src/backend/api/backend.py"

print("Checking backend code for updates...")

# Check for safe_table_to_pandas function
with open(backend_file, 'r') as f:
    content = f.read()
    
    # Check if safe_table_to_pandas exists
    if 'def safe_table_to_pandas' in content:
        print("✅ safe_table_to_pandas function found")
    else:
        print("❌ safe_table_to_pandas function NOT found")
    
    # Check for update_user_earnings call with keyword argument
    if 'conversation_delta=' in content:
        print("✅ update_user_earnings uses keyword argument")
    else:
        print("❌ update_user_earnings still using positional arguments")
    
    # Check line 991 for safe wrapper usage
    lines = content.split('\n')
    if len(lines) > 990:
        line_991 = lines[990]  # 0-indexed
        if 'safe_table_to_pandas' in line_991:
            print("✅ Line 991 uses safe_table_to_pandas")
        else:
            print(f"❌ Line 991 still has: {line_991.strip()[:60]}...")
            
    # Check for find_user_by_id with safe wrapper
    find_user_start = content.find('def find_user_by_id')
    if find_user_start > 0:
        find_user_section = content[find_user_start:find_user_start+500]
        if 'safe_table_to_pandas' in find_user_section:
            print("✅ find_user_by_id uses safe_table_to_pandas")
        else:
            print("❌ find_user_by_id doesn't use safe_table_to_pandas")