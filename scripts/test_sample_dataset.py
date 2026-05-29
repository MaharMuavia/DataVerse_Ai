import asyncio
import pandas as pd
import asyncpg
import json
from pathlib import Path
import uuid
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent

async def test_dataset_workflow():
    """Test loading sample dataset and verifying database integration"""
    
    print("=" * 70)
    print("SAMPLE DATASET WORKFLOW TEST")
    print("=" * 70)
    
    # Step 1: Load and inspect dataset
    print("\n📊 STEP 1: Loading Sample Dataset")
    print("-" * 70)
    
    csv_path = REPO_ROOT / "data" / "sample_products.csv"
    if not csv_path.exists():
        print(f"❌ File not found: {csv_path}")
        return
    
    df = pd.read_csv(csv_path)
    print(f"✅ Loaded: {csv_path.name}")
    print(f"   Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"   Columns: {', '.join(df.columns.tolist())}")
    print(f"\n   First 3 rows:")
    print(df.head(3).to_string(index=False))
    
    # Step 2: Database connection
    print("\n\n🗄️  STEP 2: Connecting to Database")
    print("-" * 70)
    
    try:
        conn = await asyncpg.connect(
            'postgresql://dataverse_user:dataverse_pass@localhost:5432/dataverse_db'
        )
        print("✅ Connected to PostgreSQL")
        
        # Get version
        version = await conn.fetchval('SELECT version()')
        print(f"   Version: {version.split(',')[0]}")
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    # Step 3: Store dataset metadata in database
    print("\n\n💾 STEP 3: Storing Dataset in Database")
    print("-" * 70)
    
    try:
        dataset_id = uuid.uuid4()
        filename = csv_path.name
        row_count = len(df)
        
        # Get numeric and categorical columns info
        column_metadata = {
            "total_columns": len(df.columns),
            "numeric_columns": df.select_dtypes(include=['number']).columns.tolist(),
            "categorical_columns": df.select_dtypes(include=['object']).columns.tolist(),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "missing_values": df.isnull().sum().astype(int).to_dict()
        }
        
        await conn.execute(
            '''INSERT INTO datasets (id, filename, row_count, column_metadata, uploaded_at)
               VALUES ($1, $2, $3, $4, $5)''',
            dataset_id, filename, row_count, json.dumps(column_metadata), datetime.now()
        )
        
        print(f"✅ Dataset stored with ID: {dataset_id}")
        print(f"   Filename: {filename}")
        print(f"   Rows: {row_count}")
        print(f"   Numeric columns: {len(column_metadata['numeric_columns'])}")
        print(f"   Categorical columns: {len(column_metadata['categorical_columns'])}")
    
    except Exception as e:
        print(f"❌ Failed to store dataset: {e}")
        await conn.close()
        return
    
    # Step 4: Verify data statistics
    print("\n\n📈 STEP 4: Dataset Statistics")
    print("-" * 70)
    
    print(f"Numeric Summary:")
    numeric_stats = df.select_dtypes(include=['number']).describe()
    for col in numeric_stats.columns:
        print(f"  {col}:")
        print(f"    - Mean: {numeric_stats[col]['mean']:.2f}")
        print(f"    - Min: {numeric_stats[col]['min']:.2f}")
        print(f"    - Max: {numeric_stats[col]['max']:.2f}")
        print(f"    - Std: {numeric_stats[col]['std']:.2f}")
    
    print(f"\nCategorical Summary:")
    for col in df.select_dtypes(include=['object']).columns:
        unique_count = df[col].nunique()
        top_value = df[col].value_counts().index[0]
        top_count = df[col].value_counts().values[0]
        print(f"  {col}: {unique_count} unique values")
        print(f"    - Top: '{top_value}' ({top_count} occurrences)")
    
    # Step 5: Query stored dataset from database
    print("\n\n🔍 STEP 5: Retrieving Dataset from Database")
    print("-" * 70)
    
    try:
        stored_dataset = await conn.fetchrow(
            'SELECT id, filename, row_count, column_metadata, uploaded_at FROM datasets WHERE id = $1',
            dataset_id
        )
        
        if stored_dataset:
            print(f"✅ Dataset retrieved successfully")
            print(f"   ID: {stored_dataset['id']}")
            print(f"   Filename: {stored_dataset['filename']}")
            print(f"   Rows in DB: {stored_dataset['row_count']}")
            print(f"   Uploaded: {stored_dataset['uploaded_at']}")
            
            metadata = json.loads(stored_dataset['column_metadata'])
            print(f"   Metadata: {metadata['total_columns']} columns tracked")
        else:
            print(f"❌ Dataset not found in database")
    
    except Exception as e:
        print(f"❌ Failed to retrieve dataset: {e}")
    
    # Step 6: Test data sampling
    print("\n\n🎯 STEP 6: Sample Data Distribution")
    print("-" * 70)
    
    print(f"Category Distribution:")
    category_counts = df['category'].value_counts()
    for cat, count in category_counts.items():
        pct = (count / len(df)) * 100
        bar = "█" * int(pct / 2)
        print(f"  {cat:15} {count:3} records {bar} {pct:.1f}%")
    
    print(f"\nRegion Distribution:")
    region_counts = df['region'].value_counts()
    for region, count in region_counts.items():
        pct = (count / len(df)) * 100
        bar = "█" * int(pct / 2)
        print(f"  {region:10} {count:3} records {bar} {pct:.1f}%")
    
    # Step 7: Price analysis
    print("\n\n💰 STEP 7: Product Pricing Analysis")
    print("-" * 70)
    
    pricing_by_category = df.groupby('category')['price'].agg(['count', 'mean', 'min', 'max'])
    print(f"{'Category':<15} {'Count':>6} {'Avg Price':>12} {'Min':>10} {'Max':>10}")
    print("-" * 60)
    for cat in pricing_by_category.index:
        row = pricing_by_category.loc[cat]
        print(f"{cat:<15} {int(row['count']):>6} ${row['mean']:>10.2f} ${row['min']:>9.2f} ${row['max']:>9.2f}")
    
    # Step 8: Sales analysis
    print("\n\n📊 STEP 8: Sales Performance")
    print("-" * 70)
    
    df['total_revenue'] = df['price'] * df['quantity_sold']
    top_products = df.nlargest(5, 'total_revenue')[['product_name', 'quantity_sold', 'price', 'total_revenue', 'customer_rating']]
    
    print(f"Top 5 Best Sellers by Revenue:")
    print(f"{'Product':<20} {'Qty':>6} {'Price':>10} {'Revenue':>12} {'Rating':>8}")
    print("-" * 60)
    for idx, row in top_products.iterrows():
        print(f"{row['product_name']:<20} {int(row['quantity_sold']):>6} ${row['price']:>9.2f} ${row['total_revenue']:>11.2f} {row['customer_rating']:>7.1f}⭐")
    
    # Final verification
    print("\n\n✅ STEP 9: Database Verification")
    print("-" * 70)
    
    try:
        table_count = await conn.fetchval('SELECT COUNT(*) FROM datasets')
        print(f"✅ Total datasets in database: {table_count}")
        
        all_datasets = await conn.fetch('SELECT filename, row_count FROM datasets ORDER BY uploaded_at DESC LIMIT 5')
        print(f"\n   Recent datasets:")
        for ds in all_datasets:
            print(f"   - {ds['filename']} ({ds['row_count']} rows)")
    
    except Exception as e:
        print(f"❌ Verification failed: {e}")
    
    await conn.close()
    
    print("\n" + "=" * 70)
    print("✅ SAMPLE DATASET TEST COMPLETED SUCCESSFULLY")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_dataset_workflow())
