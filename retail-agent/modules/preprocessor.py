import numpy as np
import pandas as pd


class Preprocessor:
    def __init__(self, df):
        self.df = df.copy()
        self.report = {}

    def run(self):
        """Execute all preprocessing steps and return cleaned DataFrame."""
        self._handle_missing()
        self._convert_dates()
        self._handle_outliers()
        self._create_features()
        return self.df

    def _handle_missing(self):
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        for col in self.df.columns:
            missing_count = int(self.df[col].isnull().sum())
            if missing_count == 0:
                continue

            if col in numeric_cols:
                fill_value = self.df[col].median()
                self.df[col] = self.df[col].fillna(fill_value)
                self.report[col] = f"filled {missing_count} missing values with median ({fill_value:.2f})"
            else:
                mode_series = self.df[col].mode(dropna=True)
                fill_value = mode_series.iloc[0] if not mode_series.empty else "Unknown"
                self.df[col] = self.df[col].fillna(fill_value)
                self.report[col] = f"filled {missing_count} missing values with mode ({fill_value})"

    def _convert_dates(self):
        for col in self.df.columns:
            if self.df[col].dtype != object:
                continue

            col_lower = col.lower()
            if not any(k in col_lower for k in ["date", "time", "day", "month", "year"]):
                continue

            converted = pd.to_datetime(self.df[col], errors="coerce")
            conversion_ratio = converted.notnull().mean()
            if conversion_ratio >= 0.7:
                self.df[col] = converted
                self.report[col] = f"converted to datetime (success ratio {conversion_ratio:.0%})"

    def _handle_outliers(self):
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            q1 = self.df[col].quantile(0.25)
            q3 = self.df[col].quantile(0.75)
            iqr = q3 - q1

            if pd.isna(iqr) or iqr == 0:
                continue

            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outlier_mask = (self.df[col] < lower) | (self.df[col] > upper)
            outliers = int(outlier_mask.sum())
            if outliers > 0:
                self.df[col] = self.df[col].clip(lower, upper)
                self.report[col] = f"capped {outliers} outliers using IQR bounds"

    def _create_features(self):
        date_cols = self.df.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns
        if len(date_cols) == 0:
            return

        date_col = date_cols[0]
        self.df["year"] = self.df[date_col].dt.year
        self.df["month"] = self.df[date_col].dt.month
        self.df["day_of_week"] = self.df[date_col].dt.dayofweek
        self.df["weekend"] = (self.df["day_of_week"] >= 5).astype(int)
        self.report["date_features"] = f"added year, month, day_of_week, weekend from {date_col}"

    def get_report(self):
        return self.report
