"""
ML engine for Clarivens — AutoML-style predictive modeling.

Key improvements over original:
- Proper target column selection strategy (not just "last numeric column")
- Minimum dataset size check
- High-cardinality target detection
- Class imbalance warning for classifiers
- Structured error codes (never raw exceptions)
"""
import io
import logging
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import mean_squared_error, r2_score, accuracy_score

logger = logging.getLogger(__name__)

# --- Thresholds ---
MIN_ROWS_FOR_ML = 50
MAX_TARGET_CARDINALITY = 50      # >50 unique values in a categorical → skip
MIN_TARGET_NON_NULL_RATIO = 0.7  # target must have ≥70% non-null values

# Semantic patterns for common business target columns (case-insensitive)
BUSINESS_TARGET_PATTERNS = [
    "revenue", "sales", "profit", "margin", "price",
    "churn", "target", "label", "class", "outcome", "result",
    "conversion", "fraud", "default", "score",
]


def select_ml_target(df: pd.DataFrame) -> Tuple[Optional[str], str]:
    """
    Selects the most appropriate target column using the following strategy:
    1. Check for semantically named business columns
    2. Use the first numeric column with sufficient non-null ratio that is not
       an obvious ID column (high-cardinality floats with all unique values)
    3. If no suitable target found, return (None, reason)

    Returns (column_name, rationale) or (None, reason_for_skip)
    """
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    all_cols = df.columns.tolist()

    # --- Step 1: Semantic name match ---
    for pattern in BUSINESS_TARGET_PATTERNS:
        for col in all_cols:
            if pattern in col.lower():
                non_null_ratio = df[col].notna().mean()
                if non_null_ratio >= MIN_TARGET_NON_NULL_RATIO:
                    return col, f"Semantic match: column '{col}' matches business pattern '{pattern}'"

    # --- Step 2: Numeric column heuristic ---
    # Prefer columns that look like measured values (not IDs)
    for col in numeric_cols:
        non_null_ratio = df[col].notna().mean()
        if non_null_ratio < MIN_TARGET_NON_NULL_RATIO:
            continue
        nunique = df[col].nunique()
        # Skip likely ID columns: all unique integer-like values
        if nunique == len(df):
            continue
        # Skip binary columns (0/1) unless they look like a label
        if nunique == 2:
            if "id" in col.lower():
                continue
        return col, f"Numeric heuristic: column '{col}' selected ({nunique} unique values, {non_null_ratio:.0%} non-null)"

    # --- Step 3: Low-cardinality categorical (classification target) ---
    for col in categorical_cols:
        nunique = df[col].nunique()
        non_null_ratio = df[col].notna().mean()
        if (
            2 <= nunique <= MAX_TARGET_CARDINALITY
            and non_null_ratio >= MIN_TARGET_NON_NULL_RATIO
        ):
            return col, f"Categorical target: column '{col}' ({nunique} classes)"

    return None, "No suitable target column could be identified. Provide a column name to enable predictive modeling."


def run_predictive_modeling(
    file_path: str,
    ext: str,
    target_column: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Runs RandomForest-based predictive modeling.

    If target_column is not provided, auto-selects using select_ml_target().
    """
    try:
        df = _load_dataframe(file_path, ext)

        # --- Size check ---
        if len(df) < MIN_ROWS_FOR_ML:
            msg = f"Dataset has only {len(df)} rows. Minimum {MIN_ROWS_FOR_ML} rows required for predictive modeling."
            return {
                "status": "skipped",
                "reason": msg,
                "message": msg,
            }

        # --- Target selection ---
        if target_column:
            if target_column not in df.columns:
                return {
                    "status": "failed",
                    "error": "TARGET_NOT_FOUND",
                    "message": f"Target column '{target_column}' was not found in the dataset.",
                }
            rationale = f"User-specified target: '{target_column}'"
        else:
            target_column, rationale = select_ml_target(df)
            if target_column is None:
                return {"status": "skipped", "reason": rationale, "message": rationale}

        logger.info("ML target selection: %s", rationale)

        # --- Prepare data ---
        df = df.dropna(subset=[target_column])
        feature_cols = df.select_dtypes(include=["number"]).columns.tolist()
        feature_cols = [c for c in feature_cols if c != target_column]

        if not feature_cols:
            msg = "No numeric feature columns available after removing the target."
            return {
                "status": "skipped",
                "reason": msg,
                "message": msg,
            }

        X = df[feature_cols].fillna(df[feature_cols].median())
        y = df[target_column]

        # Minimum 20 rows after filtering
        if len(X) < 20:
            msg = "Insufficient rows after removing nulls in target column."
            return {"status": "skipped", "reason": msg, "message": msg}

        # --- Train/test split ---
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # --- Determine task type ---
        is_classification = (
            y.dtype == "object"
            or y.nunique() <= MAX_TARGET_CARDINALITY
        )

        if is_classification:
            return _run_classifier(X_train, X_test, y_train, y_test, target_column, rationale)
        else:
            return _run_regressor(X_train, X_test, y_train, y_test, target_column, rationale)

    except Exception as e:
        logger.error("ML pipeline failed: %s", type(e).__name__)
        return {
            "status": "failed",
            "error": "ML_PIPELINE_ERROR",
            "message": "Predictive modeling could not be completed.",
        }


def _run_classifier(X_train, X_test, y_train, y_test, target: str, rationale: str) -> Dict[str, Any]:
    model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    accuracy = float(accuracy_score(y_test, preds))

    importance = _get_feature_importance(model, X_train.columns)
    class_dist = y_train.value_counts(normalize=True).to_dict()

    return {
        "status": "success",
        "task_type": "classification",
        "model_type": "RandomForestClassifier",
        "best_model": "RandomForestClassifier",
        "target_column": target,
        "target_selection_rationale": rationale,
        "metrics": {"accuracy": round(accuracy, 4)},
        "models_evaluated": {"RandomForestClassifier": {"accuracy": round(accuracy, 4)}},
        "feature_importance": importance,
        "class_distribution": {str(k): round(float(v), 4) for k, v in class_dist.items()},
    }


def _run_regressor(X_train, X_test, y_train, y_test, target: str, rationale: str) -> Dict[str, Any]:
    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
    r2 = float(r2_score(y_test, preds))

    importance = _get_feature_importance(model, X_train.columns)

    return {
        "status": "success",
        "task_type": "regression",
        "model_type": "RandomForestRegressor",
        "best_model": "RandomForestRegressor",
        "target_column": target,
        "target_selection_rationale": rationale,
        "metrics": {"rmse": round(rmse, 4), "r2": round(r2, 4)},
        "models_evaluated": {"RandomForestRegressor": {"rmse": round(rmse, 4), "r2": round(r2, 4)}},
        "feature_importance": importance,
    }


def _get_feature_importance(model, columns) -> Dict[str, float]:
    """Returns top-5 feature importances as a clean dict."""
    importance = dict(zip(columns, model.feature_importances_))
    top5 = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
    return {k: round(float(v), 4) for k, v in top5}


def _load_dataframe(file_path: str, ext: str) -> pd.DataFrame:
    if ext == "csv":
        return _read_csv_safe(file_path)
    elif ext in ("xlsx", "xls"):
        return pd.read_excel(file_path)
    elif ext == "json":
        return pd.read_json(io.open(file_path, encoding="utf-8"))
    raise ValueError(f"Unsupported file type: {ext}")


def _read_csv_safe(file_path: str) -> pd.DataFrame:
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return pd.read_csv(file_path, encoding=enc, low_memory=False)
        except (UnicodeDecodeError, ValueError):
            continue
    raise ValueError("Could not read CSV with any supported encoding.")
