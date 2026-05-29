import os
import psycopg2

env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
db_url = None
with open(env_path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip().startswith('DATABASE_URL'):
            _, v = line.split('=', 1)
            db_url = v.strip()
            break
conn_str = db_url.replace('postgresql+asyncpg://', 'postgresql://')
conn = psycopg2.connect(conn_str)
cur = conn.cursor()
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='datasets';")
rows = cur.fetchall()
print('datasets columns:')
for r in rows:
    print(r)
cur.close()
conn.close()
