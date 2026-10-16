"""guess what role each column plays."""

from __future__ import annotations

import re
from datetime import datetime

import pandas as pd

ROLES = ["id", "text", "number", "date", "category", "bool"]

DATE_FORMATS = [
    "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d.%m.%Y",
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M",
    "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%Y%m%d",
]

_ID_NAME = re.compile(r"(^|[_\s-])(id|no|nik|nip|nomor|code|kode|uuid|ssn|account|acct)($|[_\s-])|id$", re.I)


def detect_date_format(values: pd.Series) -> str | None:
    """return the first format that parses every sampled non-null string."""
    sample = values.dropna().astype(str).head(50)
    if sample.empty:
        return None
    for fmt in DATE_FORMATS:
        try:
            for v in sample:
                datetime.strptime(v, fmt)
        except ValueError:
            continue
        return fmt
    return None


def guess_role(name: str, s: pd.Series) -> str:
    non_null = s.dropna()
    unique_ratio = non_null.nunique() / max(len(non_null), 1)
    id_name = bool(_ID_NAME.search(str(name)))
    if pd.api.types.is_bool_dtype(s):
        return "bool"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "date"
    if pd.api.types.is_numeric_dtype(s):
        if id_name and pd.api.types.is_integer_dtype(s):
            return "id"
        return "number"
    if isinstance(s.dtype, pd.CategoricalDtype):
        return "category"
    if detect_date_format(s):
        return "date"
    if id_name:
        return "id"
    if len(non_null) >= 10 and unique_ratio < 0.5 and non_null.nunique() <= 50:
        return "category"
    return "text"


def default_mode(role: str) -> str:
    return "keep" if role in ("number", "bool") else "partial"
