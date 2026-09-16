"""
Secure file ingestion and dataset profiling for Clarivens.

Security measures implemented:
- Maximum file size enforcement
- Extension allowlist (csv, xlsx, xls, json only)
- MIME type validation via magic bytes
- UUID-based storage names (never original filename in paths)
- Path traversal prevention
- Encoding detection for CSV files
- Memory-safe: reads are size-limited
"""
import io
import os
import uuid
import logging
from typing import Tuple, Optional, Dict, Any

import pandas as pd

from backend.config import settings

logger = logging.getLogger(__name__)

# --- Constants ---
ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls", "json"}
MAX_BYTES = settings.max_upload_size_mb * 1024 * 1024

# Magic byte signatures for allowed file types
MAGIC_BYTES: Dict[bytes, str] = {
    b"\x50\x4B\x03\x04": "xlsx/xls",  # PK header (ZIP-based Office files)
    b"\xD0\xCF\x11\xE0": "xls",       # Legacy OLE compound document
}

UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads"
)
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ============================================================
# Validation
# ============================================================

def sanitize_filename(filename: str) -> str:
    """Strips path characters and keeps only safe characters."""
    base = os.path.basename(filename)
    return "".join(c for c in base if c.isalnum() or c in "._- ")[:100]


def validate_file_extension(filename: str) -> str:
    """
    Returns the lowercase extension if allowed, raises ValueError otherwise.
    Never uses the filename as a storage path component.
    """
    if "." not in filename:
        raise ValueError("File has no extension. Allowed: csv, xlsx, xls, json")
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"File type '.{ext}' is not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    return ext


def validate_file_size(content: bytes) -> None:
    """Raises ValueError if content exceeds the configured limit."""
    if len(content) > MAX_BYTES:
        raise ValueError(
            f"File size {len(content) // (1024*1024)}MB exceeds the "
            f"{settings.max_upload_size_mb}MB limit."
        )


def validate_mime_bytes(content: bytes, expected_ext: str) -> None:
    """
    Light magic-byte check to catch obviously mismatched MIME types.
    CSV and JSON are text-based so we check they don't start with binary headers.
    """
    if expected_ext in ("xlsx",):
        # Should start with PK or OLE header
        if not (content[:4] == b"\x50\x4B\x03\x04"):
            raise ValueError("File does not appear to be a valid Excel (.xlsx) file.")
    elif expected_ext == "xls":
        if not (content[:4] in (b"\x50\x4B\x03\x04", b"\xD0\xCF\x11\xE0")):
            raise ValueError("File does not appear to be a valid Excel (.xls) file.")
    elif expected_ext == "csv":
        # CSV must be text — reject if starts with binary magic bytes
        for magic in MAGIC_BYTES:
            if content[:4] == magic:
                raise ValueError(
                    "File appears to be binary but was uploaded as CSV. "
                    "Please check the file format."
                )
    elif expected_ext == "json":
        # JSON must start with { or [ (after optional BOM/whitespace)
        stripped = content.lstrip(b"\xef\xbb\xbf \t\r\n")  # strip BOM + whitespace
        if stripped and stripped[0] not in (ord("{"), ord("[")):
            raise ValueError("File does not appear to be valid JSON.")


# ============================================================
# Storage
# ============================================================

def generate_storage_name(ext: str, project_id: int) -> str:
    """
    Generates a UUID-based storage filename.
    Never uses the original filename in the storage path.
    """
    return f"{uuid.uuid4().hex}.{ext}"


def save_uploaded_file(
    original_filename: str,
    content: bytes,
    project_id: int,
) -> Tuple[str, str, str]:
    """
    Validates and saves an uploaded file.

    Returns (storage_name, file_path, extension).

    Raises ValueError for any validation failure.
    Never uses original_filename as a storage path component.
    """
    # 1. Validate size
    validate_file_size(content)

    # 2. Validate extension
    ext = validate_file_extension(original_filename)

    # 3. Validate magic bytes
    validate_mime_bytes(content, ext)

    # 4. Generate safe storage name
    storage_name = generate_storage_name(ext, project_id)

    # 5. Build safe project directory (numeric ID only — no user input in path)
    project_dir = os.path.join(UPLOAD_DIR, str(int(project_id)))
    os.makedirs(project_dir, exist_ok=True)

    # 6. Build final path (UUID filename, no path traversal possible)
    file_path = os.path.join(project_dir, storage_name)

    # 7. Write
    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(
        "File saved: project=%s storage_name=%s size_bytes=%s ext=%s",
        project_id, storage_name, len(content), ext,
    )

    return storage_name, file_path, ext


# ============================================================
# Profiling
# ============================================================

def analyze_dataset_profile(file_path: str, ext: str) -> Dict[str, Any]:
    """
    Reads up to the first 5,000 rows for fast profiling.
    Returns a safe schema/stats profile — no raw data.
    """
    try:
        if ext == "csv":
            df = _read_csv_safe(file_path, nrows=5000)
        elif ext in ("xlsx", "xls"):
            df = pd.read_excel(file_path, nrows=5000)
        elif ext == "json":
            df = pd.read_json(io.open(file_path, encoding="utf-8"), nrows=5000)
        else:
            return {"error": "UNSUPPORTED_FILE_TYPE", "message": f"File type '{ext}' is not supported."}

        columns = list(df.columns)
        if not columns:
            return {"error": "EMPTY_DATASET", "message": "The dataset has no columns."}

        dtypes = {str(k): str(v) for k, v in df.dtypes.items()}
        numeric_cols = list(df.select_dtypes(include=["int64", "float64"]).columns)
        categorical_cols = list(df.select_dtypes(include=["object", "category"]).columns)

        # Missing value summary (counts only — not actual values)
        missing = {col: int(df[col].isnull().sum()) for col in columns if df[col].isnull().sum() > 0}

        return {
            "columns": columns,
            "row_count_sampled": len(df),
            "column_count": len(columns),
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "inferred_types": dtypes,
            "missing_value_counts": missing,
        }
    except Exception as e:
        logger.error("Profile failed: %s", type(e).__name__)
        return {"error": "PROFILE_FAILED", "message": "Dataset profiling could not be completed."}


def _read_csv_safe(file_path: str, nrows: Optional[int] = None) -> pd.DataFrame:
    """Read CSV with encoding detection fallback."""
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            return pd.read_csv(file_path, nrows=nrows, encoding=enc, low_memory=False)
        except (UnicodeDecodeError, ValueError):
            continue
    raise ValueError("Could not decode CSV file with any supported encoding.")
