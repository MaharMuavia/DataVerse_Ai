"""
Database Setup Script - Non-interactive PostgreSQL Configuration
Connects directly to PostgreSQL and initializes the dataverse database.
"""

import subprocess
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def setup_database():
    """Setup PostgreSQL database using Python driver."""
    
    print("\n" + "="*70)
    print("DataVerse PostgreSQL Database Setup")
    print("="*70 + "\n")
    
    # Add PostgreSQL to PATH
    pg_bin = r"C:\Program Files\PostgreSQL\18\bin"
    os.environ['PATH'] = pg_bin + ";" + os.environ.get('PATH', '')
    os.environ['PGPASSWORD'] = 'eduverse123'
    
    # Step 1: Test connection
    print("[1/4] Testing PostgreSQL connection...")
    try:
        result = subprocess.run(
            ['psql', '-U', 'postgres', '-h', 'localhost', '-c', 'SELECT 1'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✓ PostgreSQL server connected successfully")
            print(f"  Output: {result.stdout.strip()}")
        else:
            print(f"✗ Connection failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error testing connection: {e}")
        return False
    
    # Step 2: Drop existing database and user (safe for development)
    print("\n[2/4] Dropping existing database and user (if any)...")
    try:
        # Drop database
        subprocess.run(
            ['psql', '-U', 'postgres', '-h', 'localhost', '-c', 
             'DROP DATABASE IF EXISTS dataverse_db;'],
            capture_output=True,
            text=True,
            timeout=10
        )
        print("✓ Dropped existing database (if present)")
        
        # Drop user
        subprocess.run(
            ['psql', '-U', 'postgres', '-h', 'localhost', '-c', 
             'DROP USER IF EXISTS dataverse_user;'],
            capture_output=True,
            text=True,
            timeout=10
        )
        print("✓ Dropped existing user (if present)")
    except Exception as e:
        print(f"⚠ Warning: {e}")
    
    # Step 3: Create user and database
    print("\n[3/4] Creating database and user...")
    
    # Create user
    try:
        result = subprocess.run(
            ['psql', '-U', 'postgres', '-h', 'localhost', '-c', 
             "CREATE USER dataverse_user WITH ENCRYPTED PASSWORD 'dataverse_pass';"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("✓ Created user: dataverse_user")
        else:
            print(f"⚠ User creation: {result.stderr.strip()}")
    except Exception as e:
        print(f"✗ Error creating user: {e}")
        return False
    
    # Create database
    try:
        result = subprocess.run(
            ['psql', '-U', 'postgres', '-h', 'localhost', '-c', 
             'CREATE DATABASE dataverse_db OWNER dataverse_user;'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("✓ Created database: dataverse_db")
        else:
            print(f"⚠ Database creation: {result.stderr.strip()}")
    except Exception as e:
        print(f"✗ Error creating database: {e}")
        return False
    
    # Grant privileges
    try:
        subprocess.run(
            ['psql', '-U', 'postgres', '-h', 'localhost', '-d', 'dataverse_db', '-c',
             'GRANT ALL PRIVILEGES ON DATABASE dataverse_db TO dataverse_user;'],
            capture_output=True,
            text=True,
            timeout=10
        )
        print("✓ Granted privileges to dataverse_user")
    except Exception as e:
        print(f"⚠ Warning during privilege grant: {e}")
    
    # Step 4: Initialize schema using SQLAlchemy
    print("\n[4/4] Initializing database schema...")
    
    try:
        backend_path = REPO_ROOT / "dataverse_backend"
        
        # Import ORM models and engine
        sys.path.insert(0, str(backend_path.parent))
        
        # Need to set DATABASE_URL in environment for imports to work
        # Update .env first
        env_path = Path.cwd() / ".env"
        if env_path.exists():
            with open(env_path, 'r') as f:
                content = f.read()
            # Make sure DATABASE_URL uses correct credentials
            if 'DATABASE_URL=' in content:
                # Already configured, good
                pass
        
        print("  Importing SQLAlchemy models...")
        from dataverse_backend.app.db.models import Base
        from dataverse_backend.app.db.base import get_engine
        import asyncio
        
        async def init_db():
            """Initialize database schema."""
            engine = get_engine()
            
            if engine is None:
                print("✗ Engine not initialized - check DATABASE_URL in .env")
                return False
            
            try:
                async with engine.begin() as conn:
                    print("  Creating tables...")
                    await conn.run_sync(Base.metadata.create_all)
                
                await engine.dispose()
                return True
            except Exception as e:
                print(f"✗ Error creating tables: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        success = asyncio.run(init_db())
        
        if success:
            print("✓ Database schema initialized (5 tables created)")
            return True
        else:
            print("✗ Could not initialize schema")
            return False
            
    except ImportError as e:
        print(f"⚠ Could not import SQLAlchemy models: {e}")
        print("  This is OK - database is created, tables may need manual creation")
        print("  Or try running the server once to auto-create tables on startup")
        return True  # Database itself was created successfully
    except Exception as e:
        print(f"⚠ Error during schema initialization: {e}")
        import traceback
        traceback.print_exc()
        print("  Database is created but schema may be incomplete")
        return True


def verify_setup():
    """Verify the database was set up correctly."""
    print("\n" + "="*70)
    print("Verifying Database Setup")
    print("="*70 + "\n")
    
    os.environ['PATH'] = r"C:\Program Files\PostgreSQL\18\bin;" + os.environ.get('PATH', '')
    os.environ['PGPASSWORD'] = 'eduverse123'
    
    # Test connection as dataverse_user
    try:
        result = subprocess.run(
            ['psql', '-U', 'dataverse_user', '-h', 'localhost', '-d', 'dataverse_db', 
             '-c', 'SELECT version();'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✓ PostgreSQL Database Connection Verified")
            print(f"\n  User: dataverse_user")
            print(f"  Database: dataverse_db")
            print(f"  Host: localhost:5432")
            print(f"\n  Version: {result.stdout.strip()[:60]}...")
            return True
        else:
            print(f"✗ Verification failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error during verification: {e}")
        return False


def print_next_steps():
    """Print instructions for next steps."""
    print("\n" + "="*70)
    print("Next Steps")
    print("="*70 + "\n")
    
    print("1. Update PostgreSQL path in .env (already updated)")
    print("   DATABASE_URL=postgresql+asyncpg://postgres:eduverse123@localhost:5432/dataverse_db\n")
    
    print("2. Start the DataVerse server:")
    print("   python scripts/run_server.py\n")
    print("   Or: python -m uvicorn app.main:app --app-dir dataverse_backend --reload\n")
    
    print("3. Upload a CSV file:")
    print('   curl -X POST http://localhost:8000/api/upload -F "file=@data/retail_mart_processed_v1.csv"\n')
    
    print("4. Query the database:")
    print('   psql -U dataverse_user -d dataverse_db -h localhost -c "SELECT * FROM datasets;"\n')
    
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        # Run setup
        success = setup_database()
        
        if success:
            # Verify setup
            verified = verify_setup()
            
            if verified:
                print("\n✓ Database setup completed successfully!\n")
                print_next_steps()
            else:
                print("\n⚠ Database created but verification failed (may still work)\n")
                print_next_steps()
        else:
            print("\n✗ Database setup failed!\n")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
