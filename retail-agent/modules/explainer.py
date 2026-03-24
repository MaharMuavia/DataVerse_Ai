import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestRegressor

try:
    import ollama
except Exception:
    ollama = None


class Explainer:
    def __init__(self, df, target_col=None, model=None, llm_model="retail-analyst"):
        self.df = df
        self.target_col = target_col
        self.model = model
        self.llm_model = llm_model
        self.explanations = {}

    def explain_features(self, query_context=""):
        """Generate feature importance and natural language explanation."""
        if self.target_col is None:
            inferred = self._infer_target_column()
            if inferred is None:
                raise ValueError("Could not infer target column. Pass --target explicitly.")
            self.target_col = inferred
            print(f"No target column provided. Using '{self.target_col}'.")

        feature_cols = [
            c for c in self.df.columns
            if c != self.target_col and self.df[c].dtype in ["int64", "float64", "int32", "float32"]
        ]
        if not feature_cols:
            raise ValueError("No numeric feature columns available for explanation.")

        X = self.df[feature_cols].fillna(0)
        y = self.df[self.target_col].fillna(0)

        if self.model is None:
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
            self.model.fit(X, y)

        shap_explainer = shap.TreeExplainer(self.model)
        shap_values = shap_explainer.shap_values(X)

        if isinstance(shap_values, list):
            shap_values = shap_values[0]

        importance = np.abs(shap_values).mean(axis=0)
        feature_importance = (
            pd.DataFrame({"feature": feature_cols, "importance": importance})
            .sort_values("importance", ascending=False)
            .reset_index(drop=True)
        )

        explanation_text = self._generate_llm_explanation(feature_importance, query_context)

        self.explanations["feature_importance"] = feature_importance.to_dict(orient="records")
        self.explanations["top_features"] = feature_importance.head(5).to_dict(orient="records")
        self.explanations["shap_explanation"] = explanation_text
        return self.explanations

    def _infer_target_column(self):
        candidate_keywords = ["sales", "revenue", "quantity", "profit"]
        for col in self.df.columns:
            if any(k in col.lower() for k in candidate_keywords):
                return col

        numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            return numeric_cols[0]

        return None

    def _generate_llm_explanation(self, feature_importance, query_context):
        prompt = f"""
Based on a retail dataset, we analyzed drivers of target variable '{self.target_col}'.
Top 5 features and scores:
{feature_importance.head(5).to_string(index=False)}

User context:
{query_context}

Explain:
1. What these features mean in retail context.
2. How they likely influence '{self.target_col}'.
3. Business actions based on these insights.
""".strip()

        if ollama is None:
            return "Ollama Python package not installed. Install dependencies and run again for LLM explanations."

        try:
            response = ollama.chat(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.get("message", {}).get("content", "No explanation returned.")
        except Exception as exc:
            return f"LLM explanation unavailable: {exc}"
