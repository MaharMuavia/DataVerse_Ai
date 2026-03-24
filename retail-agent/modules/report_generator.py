from datetime import datetime

import pandas as pd

try:
    import ollama
except Exception:
    ollama = None


class ReportGenerator:
    def __init__(self, user_query, eda_results, explanations, preprocessing_report, plots=None, llm_model="retail-analyst"):
        self.user_query = user_query
        self.eda = eda_results
        self.explanations = explanations
        self.preprocessing = preprocessing_report
        self.plots = plots or {}
        self.llm_model = llm_model

    def generate_markdown(self):
        """Generate a markdown report with all sections."""
        report = f"""# Retail Analytics Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
User Query: {self.user_query}

## 1. Data Overview
- Rows: {self.eda['shape'][0]}
- Columns: {self.eda['shape'][1]}
- Missing Values: {sum(self.eda['missing'].values())}

### Preprocessing Actions
{self._format_preprocessing()}

## 2. Exploratory Data Analysis
### Numeric Summary
{self._df_to_markdown(pd.DataFrame(self.eda.get('numeric_summary', {})))}

### Top Categories
{self._format_categories()}

### Correlation Insights
{self._format_correlation()}

## 3. Explainable Insights
### Top Driving Factors
{self._format_feature_importance()}

### AI Explanation
{self.explanations.get('shap_explanation', 'No explanation generated.')}

## 4. Recommendations
{self._generate_recommendations()}
"""
        return report

    def _format_preprocessing(self):
        if not self.preprocessing:
            return "No preprocessing steps recorded."
        return "\n".join([f"- {col}: {action}" for col, action in self.preprocessing.items()])

    def _df_to_markdown(self, df):
        if df.empty:
            return "No data."
        try:
            return df.to_markdown(index=True)
        except Exception:
            return df.to_string()

    def _format_categories(self):
        cats = self.eda.get("categorical_summary", {})
        if not cats:
            return "No categorical columns."

        lines = []
        for col, top in list(cats.items())[:3]:
            top_str = ", ".join([f"{k} ({v})" for k, v in list(top.items())[:5]])
            lines.append(f"- {col}: {top_str}")
        return "\n".join(lines)

    def _format_correlation(self):
        corr = self.eda.get("correlation", {})
        if not corr:
            return "Not enough numeric columns for correlation."

        df_corr = pd.DataFrame(corr)
        corr_pairs = []
        for i in df_corr.columns:
            for j in df_corr.columns:
                if i == j:
                    continue
                val = df_corr.loc[i, j]
                if pd.isna(val):
                    continue
                corr_pairs.append((i, j, val))

        corr_pairs.sort(key=lambda x: abs(x[2]), reverse=True)
        top_pos = [p for p in corr_pairs if p[2] > 0.5][:3]
        top_neg = [p for p in corr_pairs if p[2] < -0.5][:3]

        lines = []
        if top_pos:
            lines.append("Strong positive correlations:")
            for a, b, val in top_pos:
                lines.append(f"- {a} & {b}: {val:.2f}")

        if top_neg:
            lines.append("Strong negative correlations:")
            for a, b, val in top_neg:
                lines.append(f"- {a} & {b}: {val:.2f}")

        return "\n".join(lines) if lines else "No strong correlations found."

    def _format_feature_importance(self):
        top = self.explanations.get("top_features", [])
        if not top:
            return "No feature importance available."
        return "\n".join([f"- {item['feature']}: importance {item['importance']:.3f}" for item in top])

    def _generate_recommendations(self):
        prompt = f"""
Based on this retail analysis, suggest 3-5 actionable business recommendations.

User query: {self.user_query}
Top features: {self.explanations.get('top_features', [])}
Data shape: {self.eda['shape']}
Possible targets: {self.eda.get('possible_targets', ['unknown'])}
Correlation highlights: {self._format_correlation()}
""".strip()

        if ollama is None:
            return "Ollama package not installed. Recommendations generated without LLM are unavailable."

        try:
            response = ollama.chat(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.get("message", {}).get("content", "No recommendation text returned.")
        except Exception as exc:
            return f"Recommendation generation unavailable: {exc}"
