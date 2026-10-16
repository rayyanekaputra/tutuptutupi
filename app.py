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
from prompt_toolkit.filters import is_done
from prompt_toolkit.layout import ConditionalContainer, FormattedTextControl, HSplit, Layout, Window
from rich.console import Console
from rich.table import Table

from core import MODES, Plan, auto_plan, flatten, mask_frame, preview, sample_row, sample_rows, schema_notes, set_column
from detect import ROLES, default_mode
from fileio import EXCEL, SUPPORTED, excel_sheets, read_table, write_table
from i18n import ALL_WORDS, LANGS, set_lang, t

console = Console()
_PREVIEW_SEED = random.randrange(2**31)  # stable fake values across previews

STEPS = ("lang", "file", "index", "mask", "rows", "save")
_note = ""  # now/next hint of the current step, shown under every prompt
_file = ""  # picked file name, shown highlighted in every step header


def _badge(name: str) -> str:
    return f"[bold black on yellow] {name} [/]"


def _note_text(step: str) -> str:
    return t("note", now=t(f"now_{step}"), next=t(f"next_{step}"))


def _step(step: str) -> None:
    """decorated lowercase step header; sets the note shown under the step's prompts."""
    global _note
    _note = _note_text(step)
    title = f"[bold magenta]✦ {t('step', n=STEPS.index(step) + 1, total=len(STEPS))}[/] [bold]· {t('s_' + step)} ✦[/]"
    console.print()
    console.rule(title + (f"  {_badge(_file)}" if _file and step != "file" else ""), align="left", style="magenta")


def _with_note(q):
    """append the step note below the prompt; it disappears once answered."""
    if not _note:
        return q
    app = q.application
    note = ConditionalContainer(
        Window(FormattedTextControl([("fg:ansibrightblack italic", "".join(f"\n  {line}" for line in _note.splitlines()))]),
               wrap_lines=True, dont_extend_height=True),
        filter=~is_done)
    app.layout = Layout(HSplit([app.layout.container, note]), focused_element=app.layout.current_window)
    return q


def _ask(q):
    """unwrap a questionary prompt; ctrl+c exits cleanly."""
    answer = _with_note(q).ask()
    if answer is None:
        console.print(f"[yellow]{t('cancelled')}[/]")
        sys.exit(1)
    return answer


# frozen exe (pyinstaller): __file__ points into a temp unpack dir, so list the exe's folder instead
PROJECT_DIR = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
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
    return t("today") if days == 0 else t("yesterday") if days == 1 else t("days_ago", n=days)


def _type_path() -> Path:
    return Path(_ask(questionary.path(
        t("path_prompt"),
        validate=lambda p: Path(p).is_file() and Path(p).suffix.lower() in SUPPORTED
        or t("path_invalid", exts=", ".join(sorted(SUPPORTED))),
    )))


def _pick_file(given: str | None) -> Path:
    if given:
        path = Path(given)
        if not path.is_file():
            console.print(f"[red]{t('not_a_file')}[/] {path}")
            sys.exit(1)
        return path
    files = list_files(PROJECT_DIR)
    if not files:
        console.print(f"[yellow]{t('no_files', folder=PROJECT_DIR)}[/]")
        return _type_path()
    width = max(len(p.name) for p in files)
    choices = [
        questionary.Choice(f"{p.name.ljust(width)}   ({_human_size(p.stat().st_size)}, {_age(p.stat().st_mtime)})", value=str(p))
        for p in files
    ]
    choices.append(questionary.Choice(t("type_path"), value=TYPE_PATH))
    picked = _ask(questionary.select(
        t("pick_file"), choices=choices,
        use_search_filter=True, use_jk_keys=False))
    return _type_path() if picked == TYPE_PATH else Path(picked)


def _overview(df: pd.DataFrame) -> None:
    flat, index_names = flatten(df)
    tbl = Table(title=t("overview_title", rows=len(df), cols=len(df.columns))
                + (t("overview_index", names=", ".join(index_names)) if index_names else ""))
    for h in ("h_column", "h_dtype", "h_null", "h_unique"):
        tbl.add_column(t(h))
    for col in flat.columns:
        s = flat[col]
        tbl.add_row(str(col), str(s.dtype), f"{s.isna().mean() * 100:.1f}", str(s.nunique()))
    console.print(tbl)


def _preview(masked: pd.DataFrame, n: int = 5) -> None:
    flat, _ = flatten(masked)
    tbl = Table(title=t("preview_title"))
    for col in flat.columns:
        tbl.add_column(str(col))
    for _, row in flat.head(n).iterrows():
        tbl.add_row(*["" if pd.isna(v) else str(v) for v in row])
    console.print(tbl)


def _summary(plan: Plan, flat: pd.DataFrame, sample: pd.DataFrame) -> None:
    shown = preview(sample, replace(plan, seed=_PREVIEW_SEED))
    tbl = Table(title=t("summary_title"))
    for h in ("h_column", "h_dtype", "h_role", "h_mode", "h_sample"):
        tbl.add_column(t(h))
    for col, cp in plan.columns.items():
        warn = f" [red]{t('real_values')}[/]" if cp.mode == "keep" and cp.role in ("id", "text") else ""
        tbl.add_row(str(col), str(flat[col].dtype), cp.role, cp.mode + warn, shown.get(col, ""))
    console.print(tbl)


def _edit_column(plan: Plan, flat: pd.DataFrame, col: str) -> None:
    cp = plan.columns[col]
    role = _ask(questionary.select(t("ask_role", col=col, dtype=flat[col].dtype), choices=ROLES, default=cp.role))
    mode = _ask(questionary.select(
        t("ask_mode", col=col), choices=MODES, default=cp.mode if role == cp.role else default_mode(role)))
    if mode == "keep" and role in ("id", "text"):
        if not _ask(questionary.confirm(t("confirm_keep", col=col, role=role), default=False)):
            mode = default_mode(role)
    set_column(plan, flat, col, role, mode)
    if role == "date" and plan.columns[col].role != "date":
        console.print(f"[yellow]{t('no_date_format', col=col)}[/]")


def _choose_columns(plan: Plan, flat: pd.DataFrame) -> None:
    """show the plan; ask only about the columns the user ticks. repeat until accepted."""
    sample = sample_row(flat)
    while True:
        _summary(plan, flat, sample)
        picked = _ask(questionary.checkbox(
            t("pick_change"),
            choices=[str(c) for c in plan.columns]))
        if not picked:
            return
        for col in picked:
            _edit_column(plan, flat, col)


def _can_tui() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty() and shutil.get_terminal_size().columns >= 60


def _pick_index(df: pd.DataFrame) -> list[str]:
    """horizontal cards like the column editor; checkbox if it can't run here."""
    if _can_tui():
        try:
            from editor import pick_index
            picked = pick_index(df, _note)
        except Exception as e:  # noqa: BLE001 - any ui failure falls back to prompts
            console.print(f"[yellow]{t('index_unavailable', err=type(e).__name__)}[/]")
        else:
            if picked is None:
                console.print(f"[yellow]{t('cancelled')}[/]")
                sys.exit(1)
            return picked
    return _ask(questionary.checkbox(
        t("pick_index"),
        choices=[str(c) for c in df.columns]))


def _edit(plan: Plan, flat: pd.DataFrame) -> Plan:
    """horizontal textual editor; checkbox flow if it can't run here."""
    if _can_tui():
        try:
            from editor import edit_plan
            edited = edit_plan(flat, plan, _note)
        except Exception as e:  # noqa: BLE001 - any ui failure falls back to prompts
            console.print(f"[yellow]{t('editor_unavailable', err=type(e).__name__)}[/]")
        else:
            if edited is None:
                console.print(f"[yellow]{t('cancelled')}[/]")
                sys.exit(1)
            _summary(edited, flat, sample_row(flat))
            return edited
    _choose_columns(plan, flat)
    return plan


def _ask_rows(total: int) -> int | None:
    raw = _ask(questionary.text(
        t("ask_rows", total=total),
        default=str(min(20, total)),
        validate=lambda v: v.strip().lower() in ALL_WORDS or (v.strip().isdigit() and int(v) > 0) or t("rows_invalid"),
    ))
    return None if raw.strip().lower() in ALL_WORDS else int(raw)


def _pick_lang() -> None:
    """first question of every run; english is the default."""
    lang = _ask(questionary.select(
        "language / bahasa:", choices=[questionary.Choice(name, value=code) for code, name in LANGS.items()],
        default="en"))
    set_lang(lang)


def run(file: str | None = None, seed: int | None = None, lang: str | None = None) -> None:
    global _file
    if lang:
        set_lang(lang)
    else:
        _step("lang")
        _pick_lang()
    console.print(f"\n[bold]tutuptutupi[/] — {t('banner')}")
    _step("file")
    path = _pick_file(file)
    _file = path.name
    console.print(f"  {_badge(_file)}")

    sheet = None
    if path.suffix.lower() in EXCEL:
        sheets = excel_sheets(path)
        sheet = sheets[0] if len(sheets) == 1 else _ask(questionary.select(t("sheet"), choices=sheets))

    df = read_table(path, sheet)
    _step("index")
    if not isinstance(df.index, pd.RangeIndex) or df.index.names[0] is not None:
        index_cols = []  # parquet already carries its index
    else:
        index_cols = _pick_index(df)
    if index_cols:
        df = df.set_index(index_cols)

    _step("mask")
    _overview(df)

    plan = auto_plan(df, seed=seed)
    flat, _ = flatten(df)
    plan = _edit(plan, flat)

    if any(cp.role == "id" and cp.mode in ("partial", "full") for cp in plan.columns.values()):
        plan.id_width = int(_ask(questionary.text(
            t("ask_id_width"), default="8",
            validate=lambda v: v.isdigit() and int(v) > 0 or t("positive_number"))))

    _step("rows")
    rows = _ask_rows(len(df))
    sampled = sample_rows(df, rows, seed)
    masked = mask_frame(sampled, plan)
    _preview(masked)

    _step("save")
    default_out = path.with_name(f"{path.stem}.masked{path.suffix}")
    out = Path(_ask(questionary.path(t("save_to"), default=str(default_out))))
    if out.resolve() == path.resolve():
        console.print(f"[red]{t('no_overwrite')}[/]")
        sys.exit(1)
    if out.suffix.lower() not in SUPPORTED:
        console.print(f"[red]{t('bad_output')}[/] {out.suffix}")
        sys.exit(1)
    if not _ask(questionary.confirm(t("confirm_write", n=len(masked), out=out), default=True)):
        console.print(f"[yellow]{t('nothing_written')}[/]")
        return

    write_table(masked, out)
    notes = out.with_name(f"{out.stem}.schema.md")
    notes.write_text(schema_notes(df, plan))
    console.print()
    console.rule(f"[bold green]✦ {t('done')} ✦[/]", align="left", style="green")
    console.print(f"  {_badge(out.name)} {out}\n  {notes} [dim]{t('notes_hint')}[/]")
    console.print(f"[dim]{t('disclaimer')}[/]")
