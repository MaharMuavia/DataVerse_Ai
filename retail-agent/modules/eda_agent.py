import base64
import io

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

matplotlib.use("Agg")


class EDAAgent:
    def __init__(self, df):
        self.df = df

    def run(self):
        """Perform EDA and return a dictionary of results."""
        results = {
            "shape": self.df.shape,
            "columns": list(self.df.columns),
            "missing": self.df.isnull().sum().to_dict(),
            "dtypes": self.df.dtypes.astype(str).to_dict(),
        }

        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            results["numeric_summary"] = self.df[numeric_cols].describe().to_dict()

        cat_cols = self.df.select_dtypes(include=["object", "category"]).columns
        cat_summary = {}
        for col in cat_cols:
            cat_summary[col] = self.df[col].value_counts(dropna=False).head(10).to_dict()
        results["categorical_summary"] = cat_summary

        if len(numeric_cols) > 1:
            corr = self.df[numeric_cols].corr(numeric_only=True)
            results["correlation"] = corr.to_dict()

        possible_targets = [
            c
            for c in self.df.columns
            if any(kw in c.lower() for kw in ["sales", "revenue", "quantity", "profit"])
        ]
        results["possible_targets"] = possible_targets

        return results

    def generate_plots(self):
        """Generate base64-encoded plots for report."""
        plots = {}
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns

        if len(numeric_cols) > 0:
            fig, ax = plt.subplots(figsize=(8, 4))
            self.df[numeric_cols[0]].dropna().hist(ax=ax, bins=30)
            ax.set_title(f"Distribution of {numeric_cols[0]}")
            ax.set_xlabel(numeric_cols[0])
            ax.set_ylabel("Frequency")
            plots["histogram"] = self._fig_to_base64(fig)
            plt.close(fig)

        if len(numeric_cols) > 1:
            fig, ax = plt.subplots(figsize=(10, 8))
            sns.heatmap(self.df[numeric_cols].corr(numeric_only=True), annot=True, ax=ax, fmt=".2f")
            ax.set_title("Correlation Heatmap")
            plots["heatmap"] = self._fig_to_base64(fig)
            plt.close(fig)

        return plots

    def _fig_to_base64(self, fig):
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
