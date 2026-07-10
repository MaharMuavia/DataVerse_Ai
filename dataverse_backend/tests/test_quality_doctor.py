import pandas as pd

from app.services.quality_doctor import diagnose, apply_fixes


def _messy():
    return pd.DataFrame(
        {
            "revenue": [100.0, None, 300.0, 300.0, 100.0],
            "city": ["NY", "LA", None, "LA", "NY"],
            "flag": ["1", "2", "3", "3", "1"],
            "constant": ["x", "x", "x", "x", "x"],
        }
    )


def test_diagnose_detects_issue_categories():
    report = diagnose(_messy())
    cats = {i["category"] for i in report["issues"]}
    assert {"duplicates", "missing_values", "constant_column", "type_mismatch"} <= cats
    for issue in report["issues"]:
        assert {"id", "category", "severity", "issue", "fix", "fix_type"} <= set(issue)
    assert report["summary"]["rows"] == 5


def test_clean_dataset_with_no_issues_is_empty():
    clean = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    report = diagnose(clean)
    assert report["issues"] == []


def test_apply_fixes_cleans_dataframe():
    df = _messy()
    report = diagnose(df)
    ids = [i["id"] for i in report["issues"]]
    cleaned, summary = apply_fixes(df, ids)
    assert cleaned.duplicated().sum() == 0
    assert cleaned.isna().sum().sum() == 0
    assert "constant" not in cleaned.columns
    assert pd.api.types.is_numeric_dtype(cleaned["flag"])
    assert summary["before"]["rows"] == 5
    assert summary["after"]["rows"] <= 5
    assert summary["applied"]


def test_apply_subset_of_fixes_leaves_other_issues():
    df = _messy()
    report = diagnose(df)
    dup_id = next(i["id"] for i in report["issues"] if i["category"] == "duplicates")
    cleaned, summary = apply_fixes(df, [dup_id])
    assert cleaned.duplicated().sum() == 0
    # imputation was not requested, so missing values remain
    assert cleaned.isna().sum().sum() > 0
    assert len(summary["applied"]) == 1
