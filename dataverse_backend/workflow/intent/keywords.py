from typing import Optional

INTENT_KEYWORDS = {
    "EDA": ["missing", "null", "describe", "statistics", "summary",
            "profile", "correlation", "distribution", "shape", "info",
            "columns", "outlier", "skew", "duplicate"],

    "VIZ": ["plot", "chart", "graph", "visualize", "show me",
            "histogram", "scatter", "bar chart", "heatmap", "boxplot",
            "line chart", "pie chart", "draw"],

    "ML": ["predict", "train", "model", "classify", "regression",
           "forecast", "accuracy", "f1", "precision", "recall",
           "automl", "machine learning", "fit"],

    "XAI": ["explain", "why", "feature importance", "shap", "lime",
            "interpret", "contribution", "what caused", "reason"],

    "SQL": ["query", "select", "where", "group by", "filter",
            "count", "average", "sum", "join", "from table"],

    "CHITCHAT": ["hello", "hi", "thanks", "what can you do",
                 "help me", "who are you"],
}

def keyword_classify(query: str) -> Optional[str]:
    query_lower = query.lower()
    intent_counts = {}

    for intent, keywords in INTENT_KEYWORDS.items():
        count = sum(1 for keyword in keywords if keyword in query_lower)
        if count > 0:
            intent_counts[intent] = count

    if not intent_counts:
        return None

    # Return the intent with the most keyword hits
    return max(intent_counts, key=intent_counts.get)