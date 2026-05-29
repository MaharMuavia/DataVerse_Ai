"""
Database initialization and seeding script.
Creates demo users, workspaces, and sample data for testing.

Usage:
    python seed_database.py --create-admin
    docker-compose exec backend python app/db/seed_database.py --create-admin
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from dataverse_backend.app.db.models import User, Workspace, Base
from dataverse_backend.app.core.auth import get_password_hash
from dataverse_backend.app.core.config import settings


async def init_database():
    """Initialize database tables."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


async def create_demo_users():
    """Create demo users in the database."""
    if not settings.DATABASE_URL:
        print("ERROR: DATABASE_URL not configured")
        return False
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # Check if admin already exists
            stmt = select(User).where(User.username == "admin")
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                print("✓ Admin user already exists")
                return True
            
            # Create admin user
            admin = User(
                username="admin",
                email="admin@dataverse.ai",
                full_name="Administrator",
                hashed_password=get_password_hash("secret"),
                is_active=True,
                plan="enterprise"
            )
            session.add(admin)
            await session.commit()
            print("✓ Admin user created (username: admin, password: secret)")
            
            # Create demo user
            demo_user = User(
                username="demo",
                email="demo@dataverse.ai",
                full_name="Demo User",
                hashed_password=get_password_hash("demo"),
                is_active=True,
                plan="pro"
            )
            session.add(demo_user)
            await session.commit()
            print("✓ Demo user created (username: demo, password: demo)")
            
            # Create sample workspace for admin
            admin_workspace = Workspace(
                user_id=admin.id,
                name="Sample Analysis",
                description="Demo workspace with sample data"
            )
            session.add(admin_workspace)
            
            demo_workspace = Workspace(
                user_id=demo_user.id,
                name="Getting Started",
                description="Welcome to DataVerse!"
            )
            session.add(demo_workspace)
            
            await session.commit()
            print("✓ Sample workspaces created")
            
            return True
            
    except Exception as e:
        print(f"ERROR: Failed to create demo users: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


async def main():
    """Main initialization routine."""
    print("=" * 60)
    print("DataVerse - Database Initialization")
    print("=" * 60)
    print()
    
    if not settings.DATABASE_URL:
        print("ERROR: DATABASE_URL environment variable not set")
        return 1
    
    print(f"Database: {settings.DATABASE_URL.split('@')[-1]}")
    print()
    
    # Initialize tables
    print("Creating database tables...")
    try:
        await init_database()
        print("✓ Database tables initialized")
    except Exception as e:
        print(f"✗ Failed to initialize database: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print()
    
    # Create demo users
    print("Creating demo users...")
    success = await create_demo_users()
    if not success:
        return 1
    
    print()
    print("=" * 60)
    print("✓ Database initialization complete!")
    print("=" * 60)
    print()
    print("Demo Credentials:")
    print("  Admin   - username: admin,  password: secret")
    print("  Demo    - username: demo,   password: demo")
    print()
    print("Next steps:")
    print("  1. Start the application: docker-compose up")
    print("  2. Open http://localhost:3000 in your browser")
    print("  3. Login with demo credentials")
    print()
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
