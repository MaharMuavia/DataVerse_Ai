import pandas as pd
from pathlib import Path


class DataLoader:
    def __init__(self, filepath):
        self.filepath = Path(filepath)
        self.data = None

    def load(self):
        """Load CSV and return DataFrame with basic checks."""
        if not self.filepath.exists():
            raise FileNotFoundError(f"File {self.filepath} not found.")

        if self.filepath.suffix.lower() == ".csv":
            self.data = pd.read_csv(self.filepath)
        elif self.filepath.suffix.lower() in {".xlsx", ".xls"}:
            self.data = pd.read_excel(self.filepath)
        else:
            raise ValueError("Unsupported file type. Use .csv, .xlsx, or .xls")

        print(f"Loaded {len(self.data)} rows, {len(self.data.columns)} columns.")
        return self.data

    def get_summary(self):
        """Return basic info about the dataset."""
        if self.data is None:
            raise ValueError("Data not loaded. Call load() first.")

        return {
            "shape": self.data.shape,
            "columns": list(self.data.columns),
            "dtypes": self.data.dtypes.astype(str).to_dict(),
            "missing": self.data.isnull().sum().to_dict(),
            "head": self.data.head(3).to_dict(orient="records"),
        }
