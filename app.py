"""interactive flow. raw values are never printed; only masked ones."""

from __future__ import annotations

import random
import shutil
import sys
import time
from dataclasses import replace
from pathlib import Path

import pandas as pd
import questionary
from rich.console import Console
from rich.table import Table

from core import MODES, Plan, auto_plan, flatten, mask_frame, preview, sample_row, sample_rows, schema_notes, set_column
from detect import ROLES, default_mode
from fileio import EXCEL, SUPPORTED, excel_sheets, read_table, write_table

console = Console()
_PREVIEW_SEED = random.randrange(2**31)  # stable fake values across previews


def _ask(q):
    """unwrap a questionary prompt; ctrl+c exits cleanly."""
    answer = q.ask()
    if answer is None:
        console.print("[yellow]cancelled[/]")
        sys.exit(1)
    return answer


PROJECT_DIR = Path(__file__).resolve().parent
TYPE_PATH = "__type_path__"


def list_files(folder: Path) -> list[Path]:
    """supported files directly in folder, newest first, our own outputs hidden."""
    files = [p for p in folder.iterdir()
             if p.is_file() and p.suffix.lower() in SUPPORTED and ".masked." not in p.name]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def _human_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def _age(mtime: float) -> str:
    days = int((time.time() - mtime) // 86400)
    return "today" if days == 0 else "yesterday" if days == 1 else f"{days} days ago"


def _type_path() -> Path:
    return Path(_ask(questionary.path(
        "path to file:",
        validate=lambda p: Path(p).is_file() and Path(p).suffix.lower() in SUPPORTED
        or f"must be an existing {', '.join(sorted(SUPPORTED))} file",
    )))


def _pick_file(given: str | None) -> Path:
    if given:
        path = Path(given)
        if not path.is_file():
            console.print(f"[red]not a file:[/] {path}")
            sys.exit(1)
        return path
    files = list_files(PROJECT_DIR)
    if not files:
        console.print(f"[yellow]no supported files in {PROJECT_DIR}[/]")
        return _type_path()
    width = max(len(p.name) for p in files)
    choices = [
        questionary.Choice(f"{p.name.ljust(width)}   ({_human_size(p.stat().st_size)}, {_age(p.stat().st_mtime)})", value=str(p))
        for p in files
    ]
    choices.append(questionary.Choice("✎ type a path…", value=TYPE_PATH))
    picked = _ask(questionary.select(
        "file to mask: (arrows to move, type to filter)", choices=choices,
        use_search_filter=True, use_jk_keys=False))
    return _type_path() if picked == TYPE_PATH else Path(picked)


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


def _summary(plan: Plan, flat: pd.DataFrame, sample: pd.DataFrame) -> None:
    shown = preview(sample, replace(plan, seed=_PREVIEW_SEED))
    t = Table(title="masking plan (sample row shown masked)")
    for h in ("column", "dtype", "role", "mode", "sample"):
        t.add_column(h)
    for col, cp in plan.columns.items():
        warn = " [red]⚠ real values[/]" if cp.mode == "keep" and cp.role in ("id", "text") else ""
        t.add_row(str(col), str(flat[col].dtype), cp.role, cp.mode + warn, shown.get(col, ""))
    console.print(t)


def _edit_column(plan: Plan, flat: pd.DataFrame, col: str) -> None:
    cp = plan.columns[col]
    role = _ask(questionary.select(f"[{col}] ({flat[col].dtype}) role:", choices=ROLES, default=cp.role))
    mode = _ask(questionary.select(
        f"[{col}] mask mode:", choices=MODES, default=cp.mode if role == cp.role else default_mode(role)))
    if mode == "keep" and role in ("id", "text"):
        if not _ask(questionary.confirm(f"[{col}] keep real {role} values unmasked?", default=False)):
            mode = default_mode(role)
    set_column(plan, flat, col, role, mode)
    if role == "date" and plan.columns[col].role != "date":
        console.print(f"[yellow]couldn't detect a date format for {col}; masking it as text[/]")


def _choose_columns(plan: Plan, flat: pd.DataFrame) -> None:
    """show the plan; ask only about the columns the user ticks. repeat until accepted."""
    sample = sample_row(flat)
    while True:
        _summary(plan, flat, sample)
        picked = _ask(questionary.checkbox(
            "which columns do you want to change? (space to tick, enter with none = accept)",
            choices=[str(c) for c in plan.columns]))
        if not picked:
            return
        for col in picked:
            _edit_column(plan, flat, col)


def _can_tui() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty() and shutil.get_terminal_size().columns >= 60


def _pick_index(df: pd.DataFrame, title: str) -> list[str]:
    """horizontal cards like the column editor; checkbox if it can't run here."""
    if _can_tui():
        try:
            from editor import pick_index
            picked = pick_index(df, title)
        except Exception as e:  # noqa: BLE001 - any ui failure falls back to prompts
            console.print(f"[yellow]index picker unavailable ({type(e).__name__}); using prompts[/]")
        else:
            if picked is None:
                console.print("[yellow]cancelled[/]")
                sys.exit(1)
            return picked
    return _ask(questionary.checkbox(
        "which columns form the index? (none = plain range index, 2+ = multiindex)",
        choices=[str(c) for c in df.columns]))


def _edit(plan: Plan, flat: pd.DataFrame, title: str) -> Plan:
    """horizontal textual editor; checkbox flow if it can't run here."""
    if _can_tui():
        try:
            from editor import edit_plan
            edited = edit_plan(flat, plan, title)
        except Exception as e:  # noqa: BLE001 - any ui failure falls back to prompts
            console.print(f"[yellow]column editor unavailable ({type(e).__name__}); using prompts[/]")
        else:
            if edited is None:
                console.print("[yellow]cancelled[/]")
                sys.exit(1)
            _summary(edited, flat, sample_row(flat))
            return edited
    _choose_columns(plan, flat)
    return plan


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
    if not isinstance(df.index, pd.RangeIndex) or df.index.names[0] is not None:
        index_cols = []  # parquet already carries its index
    else:
        index_cols = _pick_index(df, path.name)
    if index_cols:
        df = df.set_index(index_cols)

    _overview(df)

    plan = auto_plan(df, seed=seed)
    flat, _ = flatten(df)
    plan = _edit(plan, flat, path.name)

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
