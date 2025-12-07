#!/usr/bin/env python
"""Test script to check if server can start and models can be imported"""
import sys
import os

print("=" * 50)
print("Testing Server Startup")
print("=" * 50)

# Test 1: Import models
print("\n1. Testing model imports...")
try:
    from models import *
    print("✅ Models imported successfully")
    print(f"   - BookHistory: {'BookHistory' in dir()}")
    print(f"   - VoucherHistory: {'VoucherHistory' in dir()}")
except Exception as e:
    print(f"❌ Error importing models: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Import main app
print("\n2. Testing main app import...")
try:
    from main import app
    print("✅ Main app imported successfully")
except Exception as e:
    print(f"❌ Error importing main app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Check database connection
print("\n3. Testing database connection...")
try:
    from database import get_db, engine
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
except Exception as e:
    print(f"⚠️ Database connection warning: {e}")
    print("   (This is OK if tables don't exist yet)")

# Test 4: Check if tables exist
print("\n4. Checking if new tables exist...")
try:
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    required_tables = ['book_history', 'voucher_history']
    for table in required_tables:
        if table in tables:
            print(f"   ✅ Table '{table}' exists")
        else:
            print(f"   ⚠️ Table '{table}' does NOT exist")
            print(f"      Run migration script: migration_add_book_voucher_history.sql")
except Exception as e:
    print(f"⚠️ Could not check tables: {e}")

print("\n" + "=" * 50)
print("Test completed!")
print("=" * 50)
print("\nIf all tests passed, try starting the server:")
print("  python main.py")
print("\nOr with uvicorn:")
print("  uvicorn main:app --host 0.0.0.0 --port 8000 --reload")

