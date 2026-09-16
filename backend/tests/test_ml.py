"""
Predictive modeling (AutoML) engine tests for Clarivens.
"""
import os
import tempfile
import pytest
import pandas as pd

from backend.services.ml_engine import run_predictive_modeling, select_ml_target

def test_select_ml_target_semantic_preference():
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "customer_name": ["A", "B", "C"],
        "monthly_revenue": [100.5, 200.0, 150.0]
    })
    target, rationale = select_ml_target(df)
    assert target == "monthly_revenue"
    assert "revenue" in rationale.lower() or "semantic" in rationale.lower()

def test_ml_skipped_on_small_dataset():
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
        f.write("a,b,target\n1,2,10\n3,4,20\n")
        tmp_path = f.name

    try:
        res = run_predictive_modeling(tmp_path, "csv")
        assert res.get("status") == "skipped"
        assert "rows" in res.get("message", "").lower() or "sample" in res.get("message", "").lower()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_ml_executes_on_valid_dataset():
    # Create dataset with > 60 rows
    data = {
        "feature_1": [i * 1.5 for i in range(70)],
        "feature_2": [i % 5 for i in range(70)],
        "target_sales": [i * 3.2 + 5.0 for i in range(70)]
    }
    df = pd.DataFrame(data)

    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
        df.to_csv(f.name, index=False)
        tmp_path = f.name

    try:
        res = run_predictive_modeling(tmp_path, "csv", target_column="target_sales")
        assert res.get("status") == "success"
        assert res.get("best_model") is not None
        assert "models_evaluated" in res
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
