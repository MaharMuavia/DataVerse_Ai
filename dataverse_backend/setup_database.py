"""
Database Setup Guide and Initialization for DataVerse Analytics Backend

This script provides step-by-step instructions for setting up PostgreSQL
and initializing the DataVerse database schema.

OPTIONS:
1. AUTOMATIC SETUP: Run this script to set everything up
2. MANUAL SETUP: Follow the SQL commands below
3. NO DATABASE: Skip this; system works without persistence
"""

import subprocess
import sys
import os
from pathlib import Path

# Colors for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(text):
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{text:^70}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")


def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")


def print_warning(text):
    print(f"{YELLOW}⚠ {text}{RESET}")


def print_error(text):
    print(f"{RED}✗ {text}{RESET}")


def check_postgres_installed():
    """Check if PostgreSQL is installed."""
    try:
        result = subprocess.run(["psql", "--version"], capture_output=True, text=True)
        print_success(f"PostgreSQL found: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print_error("PostgreSQL is not installed or 'psql' not in PATH")
        return False


def check_postgres_running():
    """Check if PostgreSQL server is running."""
    try:
        result = subprocess.run(
            ["psql", "-U", "postgres", "-c", "SELECT 1"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            print_success("PostgreSQL server is running")
            return True
        else:
            print_error("Cannot connect to PostgreSQL")
            return False
    except Exception as e:
        print_error(f"Cannot connect to PostgreSQL: {e}")
        return False


def create_database_interactive():
    """Interactive database setup."""
    print_header("PostgreSQL Database Setup")
    
    print("Configuration from .env:")
    print("  - Database: dataverse_db")
    print("  - User: dataverse_user")
    print("  - Password: dataverse_pass")
    print("  - Host: localhost")
    print("  - Port: 5432")
    
    print("\nAttempting automatic setup...\n")
    
    # Step 1: Check PostgreSQL
    if not check_postgres_installed():
        print_error("Please install PostgreSQL first")
        print("\nWINDOWS: Download from https://www.postgresql.org/download/windows/")
        print("MAC: brew install postgresql@15")
        print("LINUX: sudo apt-get install postgresql postgresql-contrib")
        return False
    
    if not check_postgres_running():
        print_warning("PostgreSQL server is not running")
        print("\nTo start PostgreSQL:")
        print("  Windows: Press WIN+R → Services → Start 'PostgreSQL'")
        print("  Mac: brew services start postgresql@15")
        print("  Linux: sudo systemctl start postgresql")
        return False
    
    # Step 2: Create user and database
    print("\nCreating database and user...")
    
    sql_commands = [
        # Create user (ignore if exists)
        "CREATE ROLE dataverse_user WITH ENCRYPTED PASSWORD 'dataverse_pass' LOGIN;",
        # Create database
        "CREATE DATABASE dataverse_db OWNER dataverse_user;",
        # Grant privileges
        "GRANT ALL PRIVILEGES ON DATABASE dataverse_db TO dataverse_user;",
        # Connect to database and set search path
        "ALTER ROLE dataverse_user SET search_path = public;",
    ]
    
    for cmd in sql_commands:
        try:
            result = subprocess.run(
                ["psql", "-U", "postgres", "-c", cmd],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                if "already exists" in result.stderr or "CREATE" in result.stdout:
                    print_success(f"Executed: {cmd[:50]}...")
            elif "already exists" in result.stderr:
                print_warning(f"Already exists: {cmd[:50]}...")
            else:
                print_warning(f"Could not execute: {cmd[:50]}... ({result.stderr})")
        except Exception as e:
            print_warning(f"Error executing SQL: {e}")
    
    # Step 3: Create tables
    print("\nInitializing database schema...")
    create_tables()
    
    print_success("Database setup complete!")
    return True


def create_tables():
    """Create the database schema by importing SQLAlchemy models."""
    try:
        # Add the dataverse_backend package to path
        backend_path = Path(__file__).parent / "dataverse_backend"
        sys.path.insert(0, str(backend_path.parent))
        
        # Import the Base and engine
        from dataverse_backend.app.db.models import Base
        from dataverse_backend.app.db.base import get_engine
        import asyncio
        
        async def init_db():
            engine = get_engine()
            if engine is None:
                print_warning("Database not configured; skipping schema creation")
                return
            
            async with engine.begin() as conn:
                # Create all tables defined in models.py
                await conn.run_sync(Base.metadata.create_all)
            
            await engine.dispose()
            print_success("All tables created successfully")
        
        # Run async init
        asyncio.run(init_db())
    except Exception as e:
        print_error(f"Could not create tables: {e}")
        print("\nTry manual SQL setup instead:")
        print_manual_sql()


def print_manual_sql():
    """Print manual SQL commands for database setup."""
    print_header("Manual SQL Setup")
    
    sql_script = """
-- Run these commands as 'postgres' user in psql:

-- 1. Create database user (if not exists)
CREATE ROLE dataverse_user WITH ENCRYPTED PASSWORD 'dataverse_pass' LOGIN;
ALTER ROLE dataverse_user SET search_path = public;

-- 2. Create database
CREATE DATABASE dataverse_db OWNER dataverse_user;

-- 3. Grant privileges
GRANT ALL PRIVILEGES ON DATABASE dataverse_db TO dataverse_user;

-- 4. Connect to the new database
\\c dataverse_db

-- 5. Create extensions (optional but recommended)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 6. Create tables from SQLAlchemy models
-- You can use Alembic migrations or run:
-- python -c "from dataverse_backend.app.db.models import Base; Base.metadata.create_all(engine)"
"""
    print(sql_script)


def print_connection_test():
    """Print commands to test the connection."""
    print_header("Test Database Connection")
    
    print("Test with psql:")
    print("  psql -U dataverse_user -d dataverse_db -h localhost")
    print("  Then type: \\dt (to list tables)")
    
    print("\nTest with Python:")
    print("""
from dataverse_backend.app.db.base import get_engine
import asyncio

async def test():
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        print(result.fetchone())

asyncio.run(test())
""")


def main():
    print_header("DataVerse Analytics - Database Setup")
    
    print(f"{BLUE}This script helps you set up PostgreSQL for DataVerse.{RESET}\n")
    
    print("Options:")
    print("1. Automatic setup (recommended)")
    print("2. Manual SQL setup")
    print("3. Skip (work without database)")
    print("4. Test connection")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == "1":
        create_database_interactive()
        print_connection_test()
    elif choice == "2":
        print_manual_sql()
    elif choice == "3":
        print_warning("Skipping database setup")
        print("Your .env file has DATABASE_URL configured.")
        print("To use the system without database, comment out DATABASE_URL in .env")
    elif choice == "4":
        print_connection_test()
    else:
        print_error("Invalid option")


if __name__ == "__main__":
    main()
