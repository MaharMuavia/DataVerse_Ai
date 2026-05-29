import pandas as pd
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
dataset_path = repo_root / "data" / "retail_mart_processed_v1.csv"
df = pd.read_csv(dataset_path, nrows=5)
print('Columns:', df.columns.tolist())
print('Dtypes:', df.dtypes.to_dict())
print('\nSample rows:\n', df.head().to_dict(orient='records'))
