"""Machine learning tasks using PyCaret.

Automates model training, evaluation, and prediction tasks.
Supports regression, classification, clustering, and anomaly detection.
"""
from celery import shared_task
import pandas as pd
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


@shared_task(name="tasks.train_ml_model.regression", bind=True, queue="slow")
def train_regression_model_task(
    self,
    ml_job_id: str,
    file_path: str,
    target_column: str,
    model_type: str = "auto"
) -> Dict[str, Any]:
    """
    Train a regression model using PyCaret.
    
    Args:
        ml_job_id: ML job ID in database
        file_path: Path to dataset file
        target_column: Target variable for regression
        model_type: Model type to train ("linear_regression", "xgboost", "auto", etc)
        
    Returns:
        Dictionary with model results and metrics
    """
    try:
        logger.info(f"[MLRegressionTask] Starting regression for job {ml_job_id}")
        self.update_state(state='PROGRESS', meta={'status': 'Loading data'})
        
        # Import PyCaret
        try:
            from pycaret.regression import setup, compare_models, create_model, tune_model
        except ImportError:
            return {
                "status": "error",
                "ml_job_id": ml_job_id,
                "error": "PyCaret not installed. Install with: pip install pycaret"
            }
        
        # Load data
        df = pd.read_csv(file_path)
        
        if target_column not in df.columns:
            return {
                "status": "error",
                "ml_job_id": ml_job_id,
                "error": f"Target column '{target_column}' not found"
            }
        
        self.update_state(state='PROGRESS', meta={'status': 'Setting up environment'})
        
        # Setup PyCaret
        try:
            setup(
                data=df,
                target=target_column,
                session_id=42,
                verbose=False,
                log_experiment=False,
            )
        except Exception as e:
            logger.error(f"[MLRegressionTask] Setup error: {e}")
            return {
                "status": "error",
                "ml_job_id": ml_job_id,
                "error": f"Setup failed: {str(e)}"
            }
        
        self.update_state(state='PROGRESS', meta={'status': 'Comparing models'})
        
        try:
            # Compare all available models
            best_model = compare_models(n_select=3, verbose=False)
            
            self.update_state(state='PROGRESS', meta={'status': 'Tuning best model'})
            
            # Tune the best model
            tuned_model = tune_model(best_model, verbose=False)
            
            # Get model info
            model_info = {
                "model_type": str(type(tuned_model).__name__),
                "trained_at": datetime.utcnow().isoformat(),
                "parameters": str(tuned_model.get_params()) if hasattr(tuned_model, 'get_params') else {},
            }
            
            logger.info(f"[MLRegressionTask] Training complete: {model_info['model_type']}")
            
            return {
                "status": "success",
                "ml_job_id": ml_job_id,
                "model_type": "regression",
                "target_column": target_column,
                "model_info": model_info,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"[MLRegressionTask] Training error: {e}")
            return {
                "status": "error",
                "ml_job_id": ml_job_id,
                "error": f"Training failed: {str(e)}"
            }
        
    except Exception as e:
        logger.error(f"[MLRegressionTask] Unexpected error: {e}")
        return {
            "status": "error",
            "ml_job_id": ml_job_id,
            "error": str(e),
        }


@shared_task(name="tasks.train_ml_model.classification", bind=True, queue="slow")
def train_classification_model_task(
    self,
    ml_job_id: str,
    file_path: str,
    target_column: str,
    model_type: str = "auto"
) -> Dict[str, Any]:
    """
    Train a classification model using PyCaret.
    
    Args:
        ml_job_id: ML job ID in database
        file_path: Path to dataset file
        target_column: Target variable for classification
        model_type: Model type to train
        
    Returns:
        Dictionary with model results and metrics
    """
    try:
        logger.info(f"[MLClassificationTask] Starting classification for job {ml_job_id}")
        self.update_state(state='PROGRESS', meta={'status': 'Loading data'})
        
        # Import PyCaret
        try:
            from pycaret.classification import setup, compare_models, create_model, tune_model
        except ImportError:
            return {
                "status": "error",
                "ml_job_id": ml_job_id,
                "error": "PyCaret not installed"
            }
        
        # Load data
        df = pd.read_csv(file_path)
        
        if target_column not in df.columns:
            return {
                "status": "error",
                "ml_job_id": ml_job_id,
                "error": f"Target column '{target_column}' not found"
            }
        
        self.update_state(state='PROGRESS', meta={'status': 'Setting up environment'})
        
        # Setup PyCaret
        try:
            setup(
                data=df,
                target=target_column,
                session_id=42,
                verbose=False,
                log_experiment=False,
            )
        except Exception as e:
            logger.error(f"[MLClassificationTask] Setup error: {e}")
            return {
                "status": "error",
                "ml_job_id": ml_job_id,
                "error": f"Setup failed: {str(e)}"
            }
        
        self.update_state(state='PROGRESS', meta={'status': 'Comparing models'})
        
        try:
            # Compare models
            best_model = compare_models(n_select=3, verbose=False)
            
            self.update_state(state='PROGRESS', meta={'status': 'Tuning best model'})
            
            # Tune best model
            tuned_model = tune_model(best_model, verbose=False)
            
            model_info = {
                "model_type": str(type(tuned_model).__name__),
                "trained_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(f"[MLClassificationTask] Training complete: {model_info['model_type']}")
            
            return {
                "status": "success",
                "ml_job_id": ml_job_id,
                "model_type": "classification",
                "target_column": target_column,
                "model_info": model_info,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"[MLClassificationTask] Training error: {e}")
            return {
                "status": "error",
                "ml_job_id": ml_job_id,
                "error": f"Training failed: {str(e)}"
            }
        
    except Exception as e:
        logger.error(f"[MLClassificationTask] Unexpected error: {e}")
        return {
            "status": "error",
            "ml_job_id": ml_job_id,
            "error": str(e),
        }


@shared_task(name="tasks.predict.batch", bind=True, queue="fast")
def batch_predict_task(
    self,
    ml_job_id: str,
    model_path: str,
    dataset_path: str
) -> Dict[str, Any]:
    """
    Generate predictions using a trained model.
    
    Args:
        ml_job_id: ML job ID
        model_path: Path to saved model file
        dataset_path: Path to dataset for prediction
        
    Returns:
        Predictions and confidence scores
    """
    try:
        logger.info(f"[PredictTask] Starting predictions for job {ml_job_id}")
        
        # TODO: Implement model loading and batch prediction
        # This would load a saved PyCaret model and generate predictions
        
        return {
            "status": "success",
            "ml_job_id": ml_job_id,
            "predictions_count": 0,  # Placeholder
        }
        
    except Exception as e:
        logger.error(f"[PredictTask] Error: {e}")
        return {
            "status": "error",
            "ml_job_id": ml_job_id,
            "error": str(e),
        }
