#!/usr/bin/env python3
"""Comprehensive Backend Audit Script"""
import sys
import os

print("=" * 70)
print("DATAVERSE BACKEND COMPREHENSIVE AUDIT")
print("=" * 70)

# Check 1: Python & Environment
print("\n[1] ENVIRONMENT CHECK")
print(f"    Python Version: {sys.version}")
print(f"    Python Executable: {sys.executable}")
print(f"    Current Dir: {os.getcwd()}")

# Check 2: Critical Dependencies
print("\n[2] DEPENDENCY CHECK")
critical_deps = ['fastapi', 'pandas', 'sqlalchemy', 'pydantic', 'asyncpg']
missing = []
for dep in critical_deps:
    try:
        __import__(dep)
        print(f"    ✓ {dep}")
    except ImportError:
        print(f"    ✗ {dep} MISSING")
        missing.append(dep)

# Check 3: Config Loading
print("\n[3] CONFIG LOADING")
try:
    from dataverse_backend.app.core.config import settings
    print(f"    ✓ Config loaded")
    print(f"    - App Name: {settings.APP_NAME}")
    print(f"    - Environment: {settings.ENVIRONMENT}")
    print(f"    - Database URL: {settings.DATABASE_URL[:30]}..." if settings.DATABASE_URL else "    - Database URL: Not configured")
except Exception as e:
    print(f"    ✗ Config failed: {e}")

# Check 4: Database Models
print("\n[4] DATABASE MODELS")
try:
    from dataverse_backend.app.db.models import User, Workspace, Dataset
    print(f"    ✓ Models imported")
    print(f"    - Tables: User, Workspace, Dataset")
except Exception as e:
    print(f"    ✗ Models import failed: {e}")

# Check 5: API Routes
print("\n[5] API ROUTES CHECK")
try:
    from dataverse_backend.app.api import auth_routes
    print(f"    ✓ Auth routes loaded")
except Exception as e:
    print(f"    ✗ Auth routes failed: {e}")

try:
    from dataverse_backend.app.api import workspace_routes
    print(f"    ✓ Workspace routes loaded")
except Exception as e:
    print(f"    ✗ Workspace routes failed: {e}")

try:
    from dataverse_backend.app.api import dataset_routes
    print(f"    ✓ Dataset routes loaded")
except Exception as e:
    print(f"    ✗ Dataset routes failed: {e}")

# Check 6: Core Services
print("\n[6] CORE SERVICES CHECK")
try:
    from dataverse_backend.app.orchestrator.agent_orchestrator import AgentOrchestrator
    print(f"    ✓ AgentOrchestrator")
except Exception as e:
    print(f"    ✗ AgentOrchestrator: {e}")

try:
    from dataverse_backend.app.data.data_manager import DataManager
    print(f"    ✓ DataManager")
except Exception as e:
    print(f"    ✗ DataManager: {e}")

print("\n" + "=" * 70)
if missing:
    print(f"⚠ ISSUES FOUND: {len(missing)} missing dependencies")
else:
    print("✓ Core checks passed")
print("=" * 70)
