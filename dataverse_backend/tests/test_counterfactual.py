"""Counterfactual XAI: smallest deterministic change that flips a prediction."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.services.counterfactual import generate_counterfactuals
from app.services.modeling import train_prediction
from app.services.xai import explain_model


def _classification_df(rows: int = 64) -> pd.DataFrame:
    # score in [20, 40); label flips at 30, so ±50% nudges can cross the boundary.
    rng = np.arange(rows)
    score = 20 + (rng % 20) + 0.5
    other = (rng % 7).astype(float)
    label = np.where(score > 30, "high", "low")
    return pd.DataFrame({"score": score, "other": other, "label": label})


def _regression_df(rows: int = 64) -> pd.DataFrame:
    rng = np.arange(rows)
    feature = 10.0 + (rng % 25)
    noise_free = feature * 10.0
    other = (rng % 5).astype(float)
    return pd.DataFrame({"feature": feature, "other": other, "outcome": noise_free})


@pytest.fixture(scope="module")
def classification_bundle():
    df = _classification_df()
    prediction, bundle, _ = train_prediction(df, target_column="label", task_type="classification")
    assert prediction["status"] == "complete"
    assert bundle is not None
    return prediction, bundle


@pytest.fixture(scope="module")
def regression_bundle():
    df = _regression_df()
    prediction, bundle, _ = train_prediction(df, target_column="outcome", task_type="regression")
    assert prediction["status"] == "complete"
    assert bundle is not None
    return prediction, bundle


def test_classification_counterfactual_flips_class(classification_bundle):
    prediction, bundle = classification_bundle
    result = generate_counterfactuals(bundle, feature_importance=prediction.get("feature_importance"))
    assert result["status"] == "complete"
    assert result["task_type"] == "classification"
    rows_with_cf = [row for row in result["rows"] if row["counterfactuals"]]
    assert rows_with_cf, "expected at least one counterfactual"
    for row in rows_with_cf:
        for cf in row["counterfactuals"]:
            assert cf["prediction_after"] != row["prediction_before"]
            assert cf["feature"]
            assert cf["sentence"]


def test_regression_counterfactual_crosses_threshold(regression_bundle):
    prediction, bundle = regression_bundle
    result = generate_counterfactuals(bundle, feature_importance=prediction.get("feature_importance"))
    assert result["status"] == "complete"
    threshold = result["threshold"]
    rows_with_cf = [row for row in result["rows"] if row["counterfactuals"]]
    assert rows_with_cf
    for row in rows_with_cf:
        before = float(row["prediction_before"])
        for cf in row["counterfactuals"]:
            after = float(cf["prediction_after"])
            # The counterfactual must land on the other side of the threshold.
            assert (before >= threshold) != (after >= threshold)


def test_counterfactuals_prefer_smallest_change(classification_bundle):
    prediction, bundle = classification_bundle
    result = generate_counterfactuals(bundle, feature_importance=prediction.get("feature_importance"))
    for row in result["rows"]:
        for cf in row["counterfactuals"]:
            assert abs(cf["pct_change"]) <= 50.0


def test_counterfactuals_are_deterministic(classification_bundle):
    prediction, bundle = classification_bundle
    a = generate_counterfactuals(bundle, feature_importance=prediction.get("feature_importance"))
    b = generate_counterfactuals(bundle, feature_importance=prediction.get("feature_importance"))
    assert a == b


def test_counterfactuals_attached_to_xai_payload(classification_bundle):
    prediction, bundle = classification_bundle
    xai = explain_model(bundle, prediction, run_xai=True)
    assert "counterfactuals" in xai
    assert xai["counterfactual_method"] == "deterministic_single_feature_search"
    assert isinstance(xai["counterfactuals"], list)


def test_no_bundle_yields_no_counterfactuals():
    xai = explain_model(None, {"status": "skipped", "reason": "too few rows"}, run_xai=True)
    assert xai.get("counterfactuals") in (None, [])
