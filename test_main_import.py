#!/usr/bin/env python3
"""Test main app import with thread timeout"""
import sys
import threading
import traceback
import time

def import_app():
    """Try to import the main app"""
    global import_result, import_error
    try:
        from dataverse_backend.app.main import app
        import_result = app
        print("✓ Main app imported successfully!")
    except Exception as e:
        import_error = (type(e).__name__, str(e))
        print(f"✗ Import failed: {e}")
        traceback.print_exc()

import_result = None
import_error = None

print("Attempting to import main app (with 10s timeout)...")
print("-" * 60)

thread = threading.Thread(target=import_app, daemon=False)
thread.start()
thread.join(timeout=10)

if thread.is_alive():
    print("\n✗ IMPORT TIMEOUT: Module import took > 10 seconds")
    print("  Likely causes:")
    print("  - Blocking I/O (database connection, file reads)")
    print("  - Heavy computation during import")
    print("  - Circular imports causing deadlock")
    sys.exit(1)

if import_error:
    name, msg = import_error
    print(f"✗ Import Error: {name}: {msg}")
    sys.exit(1)

print("-" * 60)
if import_result:
    print(f"✓ App object created: {import_result}")
    print(f"  Routes included: {len(import_result.routes)}")
    sys.exit(0)
