"""read and write tabular files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

EXCEL = {".xlsx", ".xlsm", ".xls"}
SUPPORTED = {".csv", ".tsv", ".parquet", ".json", ".jsonl", *EXCEL}


def excel_sheets(path: Path) -> list[str]:
    return pd.ExcelFile(path).sheet_names


def read_table(path: Path, sheet: str | None = None, index_cols: list[str] | None = None) -> pd.DataFrame:
    ext = path.suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(path)
    elif ext == ".tsv":
        df = pd.read_csv(path, sep="\t")
    elif ext in EXCEL:
        df = pd.read_excel(path, sheet_name=sheet or 0)
    elif ext == ".parquet":
        df = pd.read_parquet(path)
    elif ext == ".json":
        df = pd.read_json(path)
    elif ext == ".jsonl":
        df = pd.read_json(path, lines=True)
    else:
        raise ValueError(f"unsupported file type: {ext}")
    if index_cols:
        df = df.set_index(index_cols)
    return df


def _has_index(df: pd.DataFrame) -> bool:
    return any(n is not None for n in df.index.names)


def write_table(df: pd.DataFrame, path: Path) -> None:
    ext = path.suffix.lower()
    keep_index = _has_index(df)
    if ext == ".csv":
        df.to_csv(path, index=keep_index)
    elif ext == ".tsv":
        df.to_csv(path, sep="\t", index=keep_index)
    elif ext in EXCEL:
        df.to_excel(path, index=keep_index)
    elif ext == ".parquet":
        df.to_parquet(path)
    elif ext == ".json":
        (df.reset_index() if keep_index else df).to_json(path, orient="records", indent=2, date_format="iso")
    elif ext == ".jsonl":
        (df.reset_index() if keep_index else df).to_json(path, orient="records", lines=True, date_format="iso")
    else:
        raise ValueError(f"unsupported file type: {ext}")
