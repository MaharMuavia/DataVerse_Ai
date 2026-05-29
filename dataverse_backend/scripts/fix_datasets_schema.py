import os
import re
import psycopg2

env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
db_url = None
with open(env_path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip().startswith('DATABASE_URL'):
            _, v = line.split('=', 1)
            db_url = v.strip()
            break
if not db_url:
    raise SystemExit('.env DATABASE_URL not found')
# convert asyncpg style to psycopg2 connect string
conn_str = db_url.replace('postgresql+asyncpg://', 'postgresql://')
# psycopg2 expects host param in URL; this should work
print('Connecting using', conn_str)
conn = psycopg2.connect(conn_str)
conn.autocommit = False
cur = conn.cursor()
try:
    cur.execute("ALTER TABLE datasets ADD COLUMN IF NOT EXISTS workspace_id UUID;")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_datasets_workspace_id ON datasets (workspace_id);")
    # Add foreign key if not exists: check constraint name
    cur.execute("SELECT conname FROM pg_constraint WHERE conname='fk_datasets_workspace';")
    if cur.rowcount==0:
        try:
            cur.execute("ALTER TABLE datasets ADD CONSTRAINT fk_datasets_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;")
            print('Added FK constraint')
        except Exception as e:
            print('Could not add FK constraint:', e)
    conn.commit()
    print('Schema patch applied successfully')
except Exception as e:
    conn.rollback()
    print('Error applying schema patch:', e)
finally:
    cur.close()
    conn.close()
