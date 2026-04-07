import pandas as pd
import os
from tasks.celery_app import celery_app
from core.config import settings
import redis
import json

@celery_app.task(bind=True, queue="slow")
def train_model_task(self, dataset_path, target_column, model_type, session_id):
    try:
        # Load data
        if dataset_path.endswith('.xlsx'):
            df = pd.read_excel(dataset_path)
        else:
            df = pd.read_csv(dataset_path)

        # Setup PyCaret
        if model_type == "classification":
            try:
                from pycaret.classification import setup, compare_models, pull, save_model
                setup(data=df, target=target_column, session_id=42, verbose=False, html=False)
                best_model = compare_models(n_select=1, verbose=False)
                metrics = pull().iloc[0].to_dict()
            except Exception as e:
                # Fallback to sklearn
                from sklearn.ensemble import RandomForestClassifier
                from sklearn.model_selection import train_test_split
                from sklearn.metrics import accuracy_score, f1_score

                X = df.drop(columns=[target_column])
                y = df[target_column]
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

                model = RandomForestClassifier(random_state=42)
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)

                metrics = {
                    "Accuracy": accuracy_score(y_test, y_pred),
                    "F1": f1_score(y_test, y_pred, average='weighted')
                }
                best_model = model
        else:
            try:
                from pycaret.regression import setup, compare_models, pull, save_model
                setup(data=df, target=target_column, session_id=42, verbose=False, html=False)
                best_model = compare_models(n_select=1, verbose=False)
                metrics = pull().iloc[0].to_dict()
            except Exception as e:
                # Fallback to sklearn
                from sklearn.ensemble import RandomForestRegressor
                from sklearn.model_selection import train_test_split
                from sklearn.metrics import mean_squared_error, r2_score

                X = df.drop(columns=[target_column])
                y = df[target_column]
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

                model = RandomForestRegressor(random_state=42)
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)

                metrics = {
                    "MSE": mean_squared_error(y_test, y_pred),
                    "R2": r2_score(y_test, y_pred)
                }
                best_model = model

        # Save model
        os.makedirs("storage/models", exist_ok=True)
        model_path = f"storage/models/{session_id}_model"
        if hasattr(best_model, 'save_model'):  # PyCaret
            save_model(best_model, model_path)
        else:  # sklearn
            import joblib
            joblib.dump(best_model, model_path + '.pkl')
            model_path += '.pkl'

        # Push result via Redis
        r = redis.from_url(settings.REDIS_URL)
        r.publish(f"session:{session_id}:ml_result", json.dumps({
            "status": "complete",
            "model_path": model_path,
            "metrics": metrics,
            "model_type": model_type
        }))

        return {"status": "complete", "model_path": model_path, "metrics": metrics}

    except Exception as e:
        # Publish failure
        r = redis.from_url(settings.REDIS_URL)
        r.publish(f"session:{session_id}:ml_result", json.dumps({
            "status": "failed",
            "error": str(e)
        }))
        raise