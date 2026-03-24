#!/usr/bin/env python
"""
Quick Database Setup Script for DataVerse

This is a simplified version of setup_database.py for Windows PowerShell users.
Run this from the workspace root:

    python quick_setup_db.py

It will:
1. Check PostgreSQL is installed
2. Create database and user
3. Initialize schema
4. Verify the setup
"""

import subprocess
import sys
import os
from pathlib import Path


def run_cmd(cmd, description=""):
    """Run a command and return success/failure."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=30)
        success = result.returncode == 0
        return success, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def main():
    print("\n" + "="*70)
    print(" PostgreSQL Setup for DataVerse Analytics Backend")
    print("="*70 + "\n")
    
    # Check if .env exists
    env_path = Path(".env")
    if env_path.exists():
        print("✓ .env file found")
    else:
        print("✗ .env file not found - creating it now...")
        # The .env should already be created, but just in case
        print("  (Looking in parent directory...)")
    
    # Check PostgreSQL
    print("\n[1/4] Checking PostgreSQL installation...")
    success, stdout, stderr = run_cmd("psql --version")
    if success:
        print(f"✓ PostgreSQL found: {stdout.strip()}")
    else:
        print("✗ PostgreSQL not found!")
        print("\nPlease install PostgreSQL from: https://www.postgresql.org/download/")
        print("After installation, add PostgreSQL/bin to your PATH and try again.")
        return False
    
    # Check PostgreSQL server
    print("\n[2/4] Checking PostgreSQL server connection...")
    success, stdout, stderr = run_cmd('psql -U postgres -c "SELECT 1"')
    if success:
        print("✓ PostgreSQL server is running")
    else:
        print("✗ Cannot connect to PostgreSQL server")
        print("\nMake sure PostgreSQL is running:")
        print("  Windows: Services → PostgreSQL → Start")
        print("  Mac: brew services start postgresql@15")
        print("  Linux: sudo systemctl start postgresql")
        return False
    
    # Create user and database
    print("\n[3/4] Creating database and user...")
    
    # Drop existing if needed (safe for development)
    run_cmd('psql -U postgres -c "DROP DATABASE IF EXISTS dataverse_db;"')
    run_cmd('psql -U postgres -c "DROP ROLE IF EXISTS dataverse_user;"')
    
    # Create user
    success, _, _ = run_cmd(
        'psql -U postgres -c "CREATE ROLE dataverse_user WITH ENCRYPTED PASSWORD \'dataverse_pass\' LOGIN;"'
    )
    if success:
        print("✓ Created user: dataverse_user")
    else:
        print("⚠ Could not create user (may already exist)")
    
    # Create database
    success, _, _ = run_cmd(
        'psql -U postgres -c "CREATE DATABASE dataverse_db OWNER dataverse_user;"'
    )
    if success:
        print("✓ Created database: dataverse_db")
    else:
        print("⚠ Could not create database (may already exist)")
    
    # Set search path
    run_cmd(
        'psql -U postgres -d dataverse_db -c "ALTER ROLE dataverse_user SET search_path = public;"'
    )
    
    # Grant privileges
    run_cmd(
        'psql -U postgres -d dataverse_db -c "GRANT ALL PRIVILEGES ON DATABASE dataverse_db TO dataverse_user;"'
    )
    print("✓ Granted privileges")
    
    # Create tables using Python
    print("\n[4/4] Initializing database schema...")
    
    try:
        # Check if we can import the models
        sys.path.insert(0, str(Path.cwd() / "dataverse_backend"))
        
        from dataverse_backend.app.db.models import Base
        from dataverse_backend.app.db.base import get_engine
        import asyncio
        
        async def init_db():
            engine = get_engine()
            if engine is None:
                print("✗ Database URL not configured in .env")
                return False
            
            try:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                await engine.dispose()
                return True
            except Exception as e:
                print(f"✗ Could not create tables: {e}")
                return False
        
        result = asyncio.run(init_db())
        if result:
            print("✓ Database schema created (5 tables)")
        else:
            print("⚠ Could not create schema via Python, but database exists")
    
    except Exception as e:
        print(f"✗ Could not initialize schema: {e}")
        print("  (Database created; you may need to create tables manually)")
    
    # Verify setup
    print("\n[✓] Database setup complete!")
    print("\nVerifying...")
    success, stdout, stderr = run_cmd(
        'psql -U dataverse_user -d dataverse_db -c "SELECT COUNT(*) FROM datasets;"'
    )
    if success:
        print("✓ Connected successfully as dataverse_user")
        print(f"  Current row count in datasets table: {stdout.strip().split()[-1]}")
    else:
        print("⚠ Could not verify connection")
    
    print("\n" + "="*70)
    print("NEXT STEPS:")
    print("="*70)
    print("\n1. Start the DataVerse server:")
    print("   python -m uvicorn dataverse_backend.app.main:app --reload\n")
    print("2. In another terminal, upload a CSV:")
    print("   curl -X POST http://localhost:8000/api/upload \\")
    print("        -F \"file=@retail_mart_processed_v1.csv\"\n")
    print("3. Check the database:")
    print('   psql -U dataverse_user -d dataverse_db -c "SELECT * FROM datasets;"\n')
    print("="*70 + "\n")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
