import asyncio
import sqlalchemy

from dataverse_backend.app.core.config import settings
from dataverse_backend.app.db.base import get_engine

async def main():
    print('DATABASE_URL=', settings.DATABASE_URL)
    engine = get_engine()
    if engine is None:
        print('ENGINE=None - DATABASE_URL not configured or invalid')
        return
    try:
        async with engine.connect() as conn:
            res = await conn.execute(sqlalchemy.text('SELECT 1'))
            val = res.scalar_one()
            print('DB_OK:', val)
    except Exception as e:
        print('DB_ERROR:', type(e).__name__, str(e))

if __name__ == '__main__':
    asyncio.run(main())
