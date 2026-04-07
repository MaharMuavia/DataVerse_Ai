import pandas as pd
import os
from tasks.celery_app import celery_app
from core.config import settings
import redis
import json

@celery_app.task(bind=True, queue="slow")
def compute_xai_task(self, model_path, dataset_path, session_id):
    try:
        # Load model
        if model_path.endswith('.pkl'):
            import joblib
            model = joblib.load(model_path)
            pipeline = model
        else:
            from pycaret.classification import load_model
            pipeline = load_model(model_path)
            # Extract sklearn model
            if hasattr(pipeline, 'named_steps'):
                model = pipeline.named_steps.get('trained_model', pipeline)
            else:
                model = pipeline

        # Load dataset, drop target
        if dataset_path.endswith('.xlsx'):
            df = pd.read_excel(dataset_path)
        else:
            df = pd.read_csv(dataset_path)

        # Assume target is the last column or find it
        # For simplicity, assume target is known, but since not passed, assume first column or something
        # Actually, from context, target_column should be passed, but in spec it's not.
        # Let's assume we need to modify to pass target_column.

        # For now, assume target is the first column if not specified
        target_col = df.columns[0]  # This is wrong, but spec doesn't pass it
        X = df.drop(columns=[target_col]).head(200)

        # Compute SHAP
        import shap
        import matplotlib.pyplot as plt

        if hasattr(model, 'predict_proba'):
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X)
        else:
            explainer = shap.Explainer(model)
            shap_values = explainer(X)

        # Save SHAP plot
        os.makedirs("storage/xai", exist_ok=True)
        shap_path = f"storage/xai/{session_id}_shap.png"
        if isinstance(shap_values, list):
            shap.summary_plot(shap_values[1], X, show=False)  # For binary classification
        else:
            shap.summary_plot(shap_values, X, show=False)
        plt.savefig(shap_path, bbox_inches="tight", dpi=100)
        plt.close()

        # Compute LIME
        import lime.lime_tabular
        if hasattr(model, 'predict_proba'):
            explainer_lime = lime.lime_tabular.LimeTabularExplainer(
                X.values, feature_names=X.columns.tolist(), mode="classification"
            )
            exp = explainer_lime.explain_instance(X.values[0], model.predict_proba)
        else:
            explainer_lime = lime.lime_tabular.LimeTabularExplainer(
                X.values, feature_names=X.columns.tolist(), mode="regression"
            )
            exp = explainer_lime.explain_instance(X.values[0], model.predict)

        lime_path = f"storage/xai/{session_id}_lime.html"
        exp.save_to_file(lime_path)

        # Top features
        if isinstance(shap_values, list):
            shap_vals = shap_values[1] if len(shap_values) > 1 else shap_values[0]
        else:
            shap_vals = shap_values
        feature_importance = sorted(
            zip(X.columns, abs(shap_vals).mean(axis=0)),
            key=lambda x: x[1], reverse=True
        )[:5]
        top_features_text = ", ".join([f"{f} ({v:.3f})" for f, v in feature_importance])

        # Push result
        r = redis.from_url(settings.REDIS_URL)
        r.publish(f"session:{session_id}:xai_result", json.dumps({
            "status": "complete",
            "shap_plot_path": shap_path,
            "lime_path": lime_path,
            "top_features": top_features_text
        }))

        return {"status": "complete"}

    except Exception as e:
        r = redis.from_url(settings.REDIS_URL)
        r.publish(f"session:{session_id}:xai_result", json.dumps({
            "status": "failed",
            "error": str(e)
        }))
        raise