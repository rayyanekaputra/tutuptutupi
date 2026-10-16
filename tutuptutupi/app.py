"""interactive flow. raw values are never printed; only masked ones."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import questionary
from rich.console import Console
from rich.table import Table

from .core import MODES, ColumnPlan, _date_fmt, auto_plan, flatten, mask_frame, sample_rows, schema_notes
from .detect import ROLES, default_mode, guess_role
from .fileio import EXCEL, SUPPORTED, excel_sheets, read_table, write_table

console = Console()


def _ask(q):
    """unwrap a questionary prompt; ctrl+c exits cleanly."""
    answer = q.ask()
    if answer is None:
        console.print("[yellow]cancelled[/]")
        sys.exit(1)
    return answer


def _pick_file(given: str | None) -> Path:
    path = Path(given) if given else Path(_ask(questionary.path(
        "file to mask:",
        validate=lambda p: Path(p).is_file() and Path(p).suffix.lower() in SUPPORTED
        or f"must be an existing {', '.join(sorted(SUPPORTED))} file",
    )))
    if not path.is_file():
        console.print(f"[red]not a file:[/] {path}")
        sys.exit(1)
    return path


def _overview(df: pd.DataFrame) -> None:
    flat, index_names = flatten(df)
    t = Table(title=f"{len(df)} rows x {len(df.columns)} columns"
              + (f", index: {', '.join(index_names)}" if index_names else ""))
    for h in ("column", "dtype", "null %", "unique"):
        t.add_column(h)
    for col in flat.columns:
        s = flat[col]
        t.add_row(str(col), str(s.dtype), f"{s.isna().mean() * 100:.1f}", str(s.nunique()))
    console.print(t)


def _preview(masked: pd.DataFrame, n: int = 5) -> None:
    flat, _ = flatten(masked)
    t = Table(title="masked preview")
    for col in flat.columns:
        t.add_column(str(col))
    for _, row in flat.head(n).iterrows():
        t.add_row(*["" if pd.isna(v) else str(v) for v in row])
    console.print(t)


def _ask_rows(total: int) -> int | None:
    raw = _ask(questionary.text(
        f"how many rows to export? (of {total}, 'all' for everything)",
        default=str(min(20, total)),
        validate=lambda v: v.strip().lower() == "all" or (v.strip().isdigit() and int(v) > 0) or "a positive number or 'all'",
    ))
    return None if raw.strip().lower() == "all" else int(raw)


def run(file: str | None = None, seed: int | None = None) -> None:
    console.print("[bold]tutuptutupi[/] — mask data, keep the shape\n")
    path = _pick_file(file)

    sheet = None
    if path.suffix.lower() in EXCEL:
        sheets = excel_sheets(path)
        sheet = sheets[0] if len(sheets) == 1 else _ask(questionary.select("sheet:", choices=sheets))

    df = read_table(path, sheet)
    cols = [str(c) for c in df.columns]
    if not isinstance(df.index, pd.RangeIndex) or df.index.names[0] is not None:
        index_cols = []  # parquet already carries its index
    else:
        index_cols = _ask(questionary.checkbox(
            "which columns form the index? (none = plain range index, 2+ = multiindex)", choices=cols))
    if index_cols:
        df = df.set_index(index_cols)

    _overview(df)

    plan = auto_plan(df, seed=seed)
    flat, _ = flatten(df)
    console.print("\n[bold]column by column[/] — confirm the role and mask mode\n")
    for col in flat.columns:
        guess = guess_role(col, flat[col])
        role = _ask(questionary.select(
            f"[{col}] ({flat[col].dtype}) role:", choices=ROLES, default=guess))
        mode = _ask(questionary.select(
            f"[{col}] mask mode:", choices=MODES, default=default_mode(role)))
        if mode == "keep" and role in ("id", "text"):
            if not _ask(questionary.confirm(f"[{col}] keep real {role} values unmasked?", default=False)):
                mode = default_mode(role)
        cp = plan.columns[col]
        plan.columns[col] = ColumnPlan(role, mode, cp.date_format if role == cp.role else None)
        if role == "date" and not plan.columns[col].date_format:
            plan.columns[col].date_format = _date_fmt(flat[col], "date")
            if not plan.columns[col].date_format:
                console.print(f"[yellow]couldn't detect a date format for {col}; masking it as text[/]")
                plan.columns[col].role = "text"

    if any(cp.role == "id" and cp.mode in ("partial", "full") for cp in plan.columns.values()):
        plan.id_width = int(_ask(questionary.text(
            "fixed width for masked ids:", default="8",
            validate=lambda v: v.isdigit() and int(v) > 0 or "a positive number")))

    rows = _ask_rows(len(df))
    sampled = sample_rows(df, rows, seed)
    masked = mask_frame(sampled, plan)
    _preview(masked)

    default_out = path.with_name(f"{path.stem}.masked{path.suffix}")
    out = Path(_ask(questionary.path("save to:", default=str(default_out))))
    if out.resolve() == path.resolve():
        console.print("[red]refusing to overwrite the input file[/]")
        sys.exit(1)
    if out.suffix.lower() not in SUPPORTED:
        console.print(f"[red]unsupported output type:[/] {out.suffix}")
        sys.exit(1)
    if not _ask(questionary.confirm(f"write {len(masked)} masked rows to {out}?", default=True)):
        console.print("[yellow]nothing written[/]")
        return

    write_table(masked, out)
    notes = out.with_name(f"{out.stem}.schema.md")
    notes.write_text(schema_notes(df, plan))
    console.print(f"[green]done[/] -> {out}\n       {notes} (dtypes & roles, paste it next to the data)")
    console.print("[dim]partial masking still reveals part of each value: fine for an llm, not for public release.[/]")
