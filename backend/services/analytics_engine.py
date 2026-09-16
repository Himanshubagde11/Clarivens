"""
Analytics engine: data cleaning and EDA for Clarivens.
Returns structured error codes — never raw exception strings.
"""
import io
import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def _load_dataframe(file_path: str, ext: str) -> pd.DataFrame:
    """Loads a dataframe from a supported file type."""
    if ext == "csv":
        return _read_csv_safe(file_path)
    elif ext in ("xlsx", "xls"):
        return pd.read_excel(file_path)
    elif ext == "json":
        return pd.read_json(io.open(file_path, encoding="utf-8"))
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _read_csv_safe(file_path: str) -> pd.DataFrame:
    """CSV reading with encoding detection fallback."""
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return pd.read_csv(file_path, encoding=enc, low_memory=False)
        except (UnicodeDecodeError, ValueError):
            continue
    raise ValueError("Could not read CSV with any supported encoding.")


def run_data_cleaning(file_path: str, ext: str) -> Dict[str, Any]:
    """
    Cleans the dataset:
    1. Drops exact duplicate rows
    2. Fills numeric NaN with column median
    3. Fills categorical NaN with column mode or 'Unknown'
    Saves a cleaned copy with '_cleaned' suffix.
    """
    try:
        df = _load_dataframe(file_path, ext)
        original_rows = len(df)

        # 1. Drop duplicates
        df = df.drop_duplicates()
        duplicates_removed = original_rows - len(df)

        # 2. Missing value counts before cleaning
        missing_before = int(df.isnull().sum().sum())

        # 3. Fill numeric columns with median
        for col in df.select_dtypes(include=["number"]).columns:
            if df[col].isnull().any():
                median = df[col].median()
                df[col] = df[col].fillna(median if not np.isnan(median) else 0)

        # 4. Fill categorical columns with mode
        for col in df.select_dtypes(include=["object", "category"]).columns:
            if df[col].isnull().any():
                mode_series = df[col].mode()
                fill_val = mode_series.iloc[0] if not mode_series.empty else "Unknown"
                df[col] = df[col].fillna(fill_val)

        # 5. Save cleaned file (UUID-named source + _cleaned marker)
        base, dot_ext = file_path.rsplit(".", 1)
        cleaned_path = f"{base}_cleaned.{dot_ext}"

        if ext == "csv":
            df.to_csv(cleaned_path, index=False)
        elif ext in ("xlsx", "xls"):
            df.to_excel(cleaned_path, index=False)
        elif ext == "json":
            df.to_json(cleaned_path, orient="records")

        return {
            "status": "success",
            "original_rows": original_rows,
            "final_rows": len(df),
            "duplicates_removed": duplicates_removed,
            "missing_values_handled": missing_before,
            "cleaned_file_path": cleaned_path,
        }

    except Exception as e:
        logger.error("Data cleaning failed: %s", type(e).__name__)
        return {"status": "failed", "error": "CLEANING_FAILED", "message": "Data cleaning could not be completed."}


def run_eda(file_path: str, ext: str) -> Dict[str, Any]:
    """
    Performs Exploratory Data Analysis.
    Returns aggregated statistics only — no raw data rows.
    """
    try:
        df = _load_dataframe(file_path, ext)
        numeric_df = df.select_dtypes(include=["number"])

        if numeric_df.empty:
            return {
                "status": "success",
                "message": "No numeric columns found for statistical analysis.",
                "summary_statistics": {},
                "correlations": {},
                "potential_kpis": {},
            }

        # Summary stats (safe aggregated values)
        summary_stats = (
            numeric_df.describe()
            .replace({np.nan: None, np.inf: None, -np.inf: None})
            .to_dict()
        )

        # Correlation matrix (top correlations, NaN replaced)
        corr = numeric_df.corr()
        corr_clean = corr.replace({np.nan: None, np.inf: None, -np.inf: None}).to_dict()

        # KPI candidates (columns with >10 unique values, not pure IDs)
        kpis: Dict[str, float] = {}
        for col in numeric_df.columns:
            if numeric_df[col].nunique() > 10 and numeric_df[col].nunique() < len(df) * 0.95:
                total = float(numeric_df[col].sum())
                avg = float(numeric_df[col].mean())
                if not (np.isnan(total) or np.isnan(avg)):
                    kpis[f"{col}_total"] = round(total, 4)
                    kpis[f"{col}_avg"] = round(avg, 4)

        return {
            "status": "success",
            "summary_statistics": summary_stats,
            "correlations": corr_clean,
            "potential_kpis": kpis,
        }

    except Exception as e:
        logger.error("EDA failed: %s", type(e).__name__)
        return {"status": "failed", "error": "EDA_FAILED", "message": "Exploratory data analysis could not be completed."}
