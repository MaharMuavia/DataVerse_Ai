import pandas as pd
p = r"C:\Users\mouav\OneDrive\Desktop\FINAL3\retail_mart_processed_v1.csv"
df = pd.read_csv(p, nrows=5)
print('Columns:', df.columns.tolist())
print('Dtypes:', df.dtypes.to_dict())
print('\nSample rows:\n', df.head().to_dict(orient='records'))
