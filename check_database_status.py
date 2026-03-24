"""Quick database status check"""
import asyncpg
import asyncio
import uuid

async def test_db():
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='dataverse_user',
            password='dataverse_pass',
            database='dataverse_db'
        )
        
        print("\n" + "="*60)
        print("DATABASE STATUS CHECK")
        print("="*60 + "\n")
        
        # Test 1: Connection
        version = await conn.fetchval('SELECT version()')
        print('✅ Connection: SUCCESS')
        print(f'   PostgreSQL: {version.split(",")[0]}')
        
        # Test 2: Tables exist
        tables = await conn.fetch('''
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        ''')
        table_names = [t['table_name'] for t in tables]
        print(f'\n✅ Tables: {len(table_names)} tables found')
        for t in sorted(table_names):
            print(f'   ├─ {t}')
        
        # Test 3: Query capability
        count = await conn.fetchval('SELECT COUNT(*) FROM datasets')
        print(f'\n✅ SELECT Query: SUCCESS')
        print(f'   Datasets in DB: {count}')
        
        # Test 4: Insert capability  
        test_id = uuid.uuid4()
        await conn.execute(
            'INSERT INTO datasets (id, filename, row_count, column_metadata) VALUES ($1, $2, $3, $4)',
            test_id, 'test_data.csv', 100, '{}'
        )
        new_count = await conn.fetchval('SELECT COUNT(*) FROM datasets')
        print(f'\n✅ INSERT Query: SUCCESS')
        print(f'   Datasets after insert: {new_count}')
        
        # Test 5: Update capability
        await conn.execute(
            'UPDATE datasets SET row_count = $1 WHERE filename = $2',
            200, 'test_data.csv'
        )
        print(f'\n✅ UPDATE Query: SUCCESS')
        
        # Test 6: Delete capability
        await conn.execute('DELETE FROM datasets WHERE filename = $1', 'test_data.csv')
        final_count = await conn.fetchval('SELECT COUNT(*) FROM datasets')
        print(f'\n✅ DELETE Query: SUCCESS')
        print(f'   Datasets after cleanup: {final_count}')
        
        await conn.close()
        
        print(f'\n' + "="*60)
        print('✅ ALL TESTS PASSED - DATABASE IS FULLY OPERATIONAL')
        print("="*60 + "\n")
        return True
        
    except Exception as e:
        print(f'\n❌ ERROR: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_db())
