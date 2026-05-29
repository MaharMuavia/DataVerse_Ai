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
print('Connecting to', conn_str)
conn = psycopg2.connect(conn_str)
conn.autocommit = True
cur = conn.cursor()
# Drop tables in an order to satisfy FKs
tables = ['agent_logs','ml_jobs','messages','conversations','reports','analysis_results','agent_runs','user_queries','datasets','workspaces','users']
for t in tables:
    try:
        cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE;")
        print('Dropped', t)
    except Exception as e:
        print('Error dropping', t, e)
cur.close()
conn.close()
print('Done')
