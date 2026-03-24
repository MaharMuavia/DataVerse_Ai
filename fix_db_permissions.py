"""
Fix PostgreSQL permissions for dataverse_user
"""

import asyncpg
import asyncio


async def fix_permissions():
    """Grant necessary permissions to dataverse_user."""
    
    print("\n" + "="*70)
    print("Fixing PostgreSQL Permissions")
    print("="*70 + "\n")
    
    try:
        # Connect as postgres (admin)
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='1234',
            database='dataverse_db'
        )
        
        # Grant all permissions on all tables
        print("[1/4] Granting schema usage...")
        await conn.execute('GRANT USAGE ON SCHEMA public TO dataverse_user;')
        print("✓ Schema usage granted")
        
        print("[2/4] Granting table permissions...")
        await conn.execute('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO dataverse_user;')
        print("✓ All table privileges granted")
        
        print("[3/4] Granting sequence permissions...")
        await conn.execute('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO dataverse_user;')
        print("✓ Sequence privileges granted")
        
        print("[4/4] Setting default privileges...")
        await conn.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO dataverse_user;')
        await conn.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO dataverse_user;')
        print("✓ Default privileges set")
        
        await conn.close()
        
        print("\n✓ Permissions fixed!\n")
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}\n")
        return False


if __name__ == "__main__":
    asyncio.run(fix_permissions())
