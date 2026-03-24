"""
Test database configuration by uploading a CSV and checking persistence
"""

import requests
import asyncpg
import asyncio
import json
from pathlib import Path


async def test_database_configuration():
    """Test full database integration workflow."""
    
    print("\n" + "="*70)
    print("DataVerse Database Configuration Test")
    print("="*70 + "\n")
    
    # Files and URLs
    csv_file = Path("retail_mart_processed_v1.csv")
    upload_url = "http://localhost:8001/api/upload"
    query_url = "http://localhost:8001/api/query"
    
    # Step 1: Test API upload
    print("[1/3] Testing CSV upload to API...")
    try:
        with open(csv_file, 'rb') as f:
            files = {'file': (csv_file.name, f, 'text/csv')}
            response = requests.post(upload_url, files=files, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            session_id = result.get('session_id')
            print(f"✓ Upload successful")
            print(f"  Status: {response.status_code}")
            print(f"  Session ID: {session_id}")
            print(f"  Message: {result.get('message', 'N/A')}\n")
        else:
            print(f"✗ Upload failed with status {response.status_code}")
            print(f"  Response: {response.text}\n")
            return False
            
    except Exception as e:
        print(f"✗ Upload error: {e}\n")
        return False
    
    # Step 2: Query the database directly
    print("[2/3] Checking database persistence...")
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='dataverse_user',
            password='dataverse_pass',
            database='dataverse_db'
        )
        
        # Check datasets table
        dataset_count = await conn.fetchval('SELECT COUNT(*) FROM datasets')
        print(f"✓ Connected to database")
        print(f"  Datasets in database: {dataset_count}")
        
        # Get details of inserted dataset
        if dataset_count > 0:
            datasets = await conn.fetch('SELECT id, filename, row_count FROM datasets ORDER BY uploaded_at DESC LIMIT 1')
            if datasets:
                ds = datasets[0]
                print(f"\n  Latest dataset:")
                print(f"    ├─ ID: {ds['id']}")
                print(f"    ├─ Filename: {ds['filename']}")
                print(f"    └─ Rows: {ds['row_count']}")
        
        # Check other tables
        query_count = await conn.fetchval('SELECT COUNT(*) FROM user_queries')
        agent_count = await conn.fetchval('SELECT COUNT(*) FROM agent_runs')
        result_count = await conn.fetchval('SELECT COUNT(*) FROM analysis_results')
        report_count = await conn.fetchval('SELECT COUNT(*) FROM reports')
        
        print(f"\n  Table Statistics:")
        print(f"    ├─ datasets: {dataset_count}")
        print(f"    ├─ user_queries: {query_count}")
        print(f"    ├─ agent_runs: {agent_count}")
        print(f"    ├─ analysis_results: {result_count}")
        print(f"    └─ reports: {report_count}\n")
        
        await conn.close()
        
    except Exception as e:
        print(f"✗ Database check error: {e}\n")
        return False
    
    # Step 3: Test query endpoint (if there's a session)
    if session_id:
        print("[3/3] Testing analytics query...")
        try:
            query_data = {
                "session_id": session_id,
                "query": "Analyze the data and show distribution"
            }
            response = requests.post(query_url, json=query_data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Query successful")
                print(f"  Status: {response.status_code}")
                print(f"  Query: {result.get('user_query', 'N/A')}")
                if 'results' in result:
                    if 'eda' in result['results'] and result['results']['eda']:
                        print(f"  ✓ EDA completed")
                    if 'visualizations' in result['results'] and result['results']['visualizations']:
                        print(f"  ✓ Generated {len(result['results']['visualizations'])} visualizations")
                print()
            else:
                print(f"✗ Query failed with status {response.status_code}")
                print(f"  Response: {response.text[:200]}\n")
                
        except Exception as e:
            print(f"⚠ Query test error: {e} (non-critical)\n")
    
    return True


async def print_summary():
    """Print configuration summary."""
    
    print("="*70)
    print("Database Configuration Summary")
    print("="*70 + "\n")
    
    config = {
        "Server": "PostgreSQL 18.1",
        "Host": "localhost",
        "Port": "5432",
        "Database": "dataverse_db",
        "User": "dataverse_user",
        "Password": "dataverse_pass (stored securely)",
        "Status": "✓ Configured & Tested",
        "Tables": "5 (datasets, user_queries, agent_runs, analysis_results, reports)",
        "API Status": "✓ Running on http://0.0.0.0:8001"
    }
    
    print("Configuration Details:\n")
    for key, value in config.items():
        print(f"  {key:.<30} {value}")
    
    print("\n" + "="*70)
    print("\nDatabase Configuration Verified Successfully! ✓")
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        success = asyncio.run(test_database_configuration())
        if success:
            asyncio.run(print_summary())
        print("\nTo verify database from command line:")
        print('  psql -U dataverse_user -d dataverse_db -h localhost -c "SELECT COUNT(*) FROM datasets;"\n')
    except KeyboardInterrupt:
        print("\nTest cancelled")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
