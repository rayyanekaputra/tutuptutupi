"""apply a masking plan to a whole dataframe, index included."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

import maskers as m
from detect import default_mode, detect_date_format, guess_role

MODES = ["partial", "full", "fake", "keep"]


@dataclass
class ColumnPlan:
    role: str
    mode: str
    date_format: str | None = None


@dataclass
class Plan:
    columns: dict[str, ColumnPlan] = field(default_factory=dict)
    id_width: int = 8
    seed: int | None = None


def flatten(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """move index levels into columns so they are masked like any column."""
    names = [n for n in df.index.names if n is not None]
    if names:
        return df.reset_index(), names
    return df, []


def auto_plan(df: pd.DataFrame, id_width: int = 8, seed: int | None = None) -> Plan:
    flat, _ = flatten(df)
    plan = Plan(id_width=id_width, seed=seed)
    for col in flat.columns:
        role = guess_role(col, flat[col])
        plan.columns[col] = ColumnPlan(role, default_mode(role), _date_fmt(flat[col], role))
    return plan


def _date_fmt(s: pd.Series, role: str) -> str | None:
    if role != "date":
        return None
    if pd.api.types.is_datetime64_any_dtype(s):
        has_time = (s.dropna().dt.normalize() != s.dropna()).any()
        return "%Y-%m-%d %H:%M:%S" if has_time else "%Y-%m-%d"
    return detect_date_format(s)


def sample_rows(df: pd.DataFrame, rows: int | None, seed: int | None = None) -> pd.DataFrame:
    if rows is None or rows >= len(df):
        return df
    return df.sample(n=rows, random_state=seed).sort_index()


def mask_series(s: pd.Series, cp: ColumnPlan, keyer: m.Keyer, id_width: int) -> pd.Series:
    if cp.mode == "keep":
        return s
    fn = _value_fn(s, cp, keyer, id_width)
    out = s.map(lambda v: v if _isna(v) else fn(v))
    if cp.mode == "fake" and _keeps_dtype(s):
        try:
            return out.astype(s.dtype)
        except (TypeError, ValueError):
            return out
    return out.astype("object")


def _value_fn(s: pd.Series, cp: ColumnPlan, keyer: m.Keyer, w: int):
    role, mode = cp.role, cp.mode
    is_dt = pd.api.types.is_datetime64_any_dtype(s)
    if role == "id":
        if mode == "partial":
            return lambda v: m.partial_id(v, w, keyer)
        if mode == "full":
            return lambda v: m.full_id(v, w)
        if pd.api.types.is_integer_dtype(s):
            return lambda v: m.fake_int(v, keyer)
        return lambda v: m.fake_text(v, keyer)
    if role == "date" and cp.date_format:
        fmt = cp.date_format
        parse = (lambda v: v.to_pydatetime()) if is_dt else (lambda v: datetime.strptime(str(v), fmt))
        if mode == "partial":
            return lambda v: m.partial_date(parse(v), fmt)
        if mode == "full":
            return lambda v: m.full_text(parse(v).strftime(fmt))
        if is_dt:
            return lambda v: pd.Timestamp(m.fake_date(parse(v), keyer))
        return lambda v: m.fake_date(parse(v), keyer).strftime(fmt)
    if mode == "partial":
        return m.partial_text
    if mode == "full":
        return m.full_text
    # fake
    if pd.api.types.is_bool_dtype(s):
        return lambda v: m.fake_bool(v, keyer)
    if pd.api.types.is_integer_dtype(s):
        return lambda v: m.fake_int(v, keyer)
    if pd.api.types.is_float_dtype(s):
        return lambda v: m.fake_float(v, keyer)
    if role == "category":
        cats = {v: f"{s.name}_{i}" for i, v in enumerate(pd.unique(s.dropna()))}
        return lambda v: cats[v]
    return lambda v: m.fake_text(v, keyer)


def _keeps_dtype(s: pd.Series) -> bool:
    return (pd.api.types.is_numeric_dtype(s) or pd.api.types.is_bool_dtype(s)
            or pd.api.types.is_datetime64_any_dtype(s))


def _isna(v: object) -> bool:
    try:
        return bool(pd.isna(v))
    except (TypeError, ValueError):
        return False


def mask_frame(df: pd.DataFrame, plan: Plan) -> pd.DataFrame:
    keyer = m.Keyer(plan.seed)
    flat, index_names = flatten(df)
    out = flat.copy()
    for col in flat.columns:
        cp = plan.columns.get(col)
        if cp is None:
            raise KeyError(f"no plan for column {col!r}")
        out[col] = mask_series(flat[col], cp, keyer, plan.id_width)
    return out.set_index(index_names) if index_names else out


def schema_notes(df: pd.DataFrame, plan: Plan) -> str:
    """markdown describing original dtypes, so an llm knows what masked columns really were."""
    flat, index_names = flatten(df)
    lines = [
        "# dataset shape",
        "",
        f"- rows (original): {len(df)}",
        f"- index: {', '.join(index_names) if index_names else 'range index'}"
        + (" (multiindex)" if len(index_names) > 1 else ""),
        "",
        "| column | original dtype | role | mask | date format | null % |",
        "|---|---|---|---|---|---|",
    ]
    for col in flat.columns:
        cp = plan.columns[col]
        null_pct = f"{flat[col].isna().mean() * 100:.1f}"
        lines.append(f"| {col} | {flat[col].dtype} | {cp.role} | {cp.mode} | {cp.date_format or ''} | {null_pct} |")
    lines += ["", f"ids are masked to a fixed width of {plan.id_width} characters; `*` marks hidden characters."]
    return "\n".join(lines) + "\n"
