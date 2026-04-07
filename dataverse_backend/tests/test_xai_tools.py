import pytest

from app.agents.core.tool_registry import SessionContext
from app.agents.tools.counterfactual_explainer import CounterfactualExplainerTool
from app.agents.tools.explain_model_global import ExplainModelGlobalTool
from app.agents.tools.explain_prediction_local import ExplainPredictionLocalTool
from app.agents.tools.train_classifier import TrainClassifierTool


@pytest.fixture
def xai_dataset_csv(tmp_path, sample_dataframe):
    dataset = sample_dataframe[["price", "quantity", "customer_age", "revenue", "is_premium"]].copy()
    dataset = dataset.head(180)
    csv_path = tmp_path / "xai_dataset.csv"
    dataset.to_csv(csv_path, index=False)
    return str(csv_path)


@pytest.mark.asyncio
async def test_global_and_local_xai_tools(monkeypatch, tmp_path, xai_dataset_csv):
    monkeypatch.setenv("DATAVERSE_MODEL_DIR", str(tmp_path / "models"))
    session = SessionContext(session_id="xai_session", dataset_path=xai_dataset_csv)

    train_result = await TrainClassifierTool().execute(
        {
            "target_col": "is_premium",
            "feature_cols": ["price", "quantity", "customer_age", "revenue"],
            "metric": "f1",
        },
        session,
    )
    assert train_result.success is True

    model_id = train_result.data["model_id"]

    global_result = await ExplainModelGlobalTool().execute(
        {"model_id": model_id, "n_features": 4},
        session,
    )
    assert global_result.success is True
    assert global_result.data["feature_importance"]
    assert global_result.data["method"] in {
        "Explainer",
        "TreeExplainer",
        "LinearExplainer",
        "KernelExplainer",
        "model_importance",
    }

    local_result = await ExplainPredictionLocalTool().execute(
        {"model_id": model_id, "row_index": 3},
        session,
    )
    assert local_result.success is True
    assert local_result.data["contributions"]
    assert local_result.data["method"] in {"shap", "lime"}


@pytest.mark.asyncio
async def test_counterfactual_tool_returns_model_backed_scenarios(monkeypatch, tmp_path, xai_dataset_csv):
    monkeypatch.setenv("DATAVERSE_MODEL_DIR", str(tmp_path / "models"))
    session = SessionContext(session_id="cf_session", dataset_path=xai_dataset_csv)

    train_result = await TrainClassifierTool().execute(
        {
            "target_col": "is_premium",
            "feature_cols": ["price", "quantity", "customer_age", "revenue"],
            "metric": "accuracy",
        },
        session,
    )
    assert train_result.success is True

    model_id = train_result.data["model_id"]

    counterfactual_result = await CounterfactualExplainerTool().execute(
        {"model_id": model_id, "row_index": 5, "n_counterfactuals": 2},
        session,
    )
    assert counterfactual_result.success is True
    assert counterfactual_result.data["method"] == "nearest_observed_counterfactual"
    assert len(counterfactual_result.data["counterfactuals"]) >= 1
