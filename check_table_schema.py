import asyncio
import asyncpg

async def check_schema():
    conn = await asyncpg.connect('postgresql://dataverse_user:dataverse_pass@localhost:5432/dataverse_db')
    columns = await conn.fetch('''
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'datasets'
        ORDER BY ordinal_position
    ''')
    print('Columns in datasets table:')
    for col in columns:
        nullable = 'YES' if col['is_nullable'] == 'YES' else 'NO'
        print(f'  - {col["column_name"]:20} {col["data_type"]:15} nullable={nullable}')
    await conn.close()

asyncio.run(check_schema())
