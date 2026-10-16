"""horizontal column editor: one card per column, one masked sample row."""

from __future__ import annotations

import copy
import random
from dataclasses import replace

import pandas as pd
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import HorizontalScroll
from textual.widgets import Static

from core import MODES, Plan, preview, sample_row, set_column
from detect import ROLES, default_mode

CARD_WIDTH = 22
FIELDS = ("role", "mode")


def _risky(cp) -> bool:
    return cp.mode == "keep" and cp.role in ("id", "text")


class ColumnCard(Static):
    pass


class ColumnEditor(App[Plan | None]):
    """returns the edited plan on enter, None on esc."""

    CSS = f"""
    Screen {{ layout: vertical; }}
    #title {{ height: 1; padding: 0 1; background: $panel; }}
    #cols {{ height: auto; }}
    ColumnCard {{ width: {CARD_WIDTH}; height: auto; border: round $panel-lighten-2; padding: 0 1; }}
    ColumnCard.selected {{ border: heavy $accent; }}
    #status {{ height: auto; padding: 0 1; }}
    #help {{ dock: bottom; height: 1; padding: 0 1; background: $panel; color: $text-muted; }}
    """

    BINDINGS = [
        Binding("left", "move(-1)", "column", show=False, priority=True),
        Binding("right", "move(1)", "column", show=False, priority=True),
        Binding("up", "cycle(-1)", "change", show=False, priority=True),
        Binding("down", "cycle(1)", "change", show=False, priority=True),
        Binding("tab", "switch_field", "role/mode", show=False, priority=True),
        Binding("enter", "done", "done", show=False, priority=True),
        Binding("escape", "cancel", "cancel", show=False, priority=True),
    ]

    def __init__(self, flat: pd.DataFrame, plan: Plan, title: str = "") -> None:
        super().__init__()
        self.flat = flat
        self.plan = copy.deepcopy(plan)
        self.sample = sample_row(flat)
        self.preview_seed = plan.seed if plan.seed is not None else random.randrange(2**31)
        self.cols = list(self.plan.columns)
        self.idx = 0
        self.field = 0
        self.confirming = False
        self.heading = title

    def compose(self) -> ComposeResult:
        yield Static(f"[b]tutuptutupi[/b] — {self.heading}  ({len(self.flat)} rows, {len(self.cols)} columns)", id="title")
        with HorizontalScroll(id="cols"):
            for i, _ in enumerate(self.cols):
                yield ColumnCard(id=f"c{i}")
        yield Static(id="status")
        yield Static("←/→ column   ↑/↓ change   tab role/mode   enter done   esc cancel", id="help")

    def on_mount(self) -> None:
        self.refresh_cards()

    # ---------- rendering ----------

    def refresh_cards(self) -> None:
        shown = preview(self.sample, replace(self.plan, seed=self.preview_seed))
        for i, col in enumerate(self.cols):
            card = self.query_one(f"#c{i}", ColumnCard)
            card.update(self._card_text(i, col, shown.get(col, "")))
            card.set_class(i == self.idx, "selected")
        selected = self.query_one(f"#c{self.idx}", ColumnCard)
        self.query_one("#cols", HorizontalScroll).scroll_to_widget(selected, animate=False)
        self._status()

    def _card_text(self, i: int, col: str, sample: str) -> Text:
        cp = self.plan.columns[col]
        inner = CARD_WIDTH - 4
        t = Text(no_wrap=True, overflow="ellipsis")
        t.append(_fit(str(col), inner) + "\n", style="bold")
        t.append(_fit(str(self.flat[col].dtype), inner) + "\n", style="dim")
        t.append("─" * inner + "\n", style="dim")
        for f, value in zip(FIELDS, (cp.role, cp.mode)):
            active = i == self.idx and FIELDS[self.field] == f
            t.append(f"{f}: ", style="dim")
            t.append(f"{'▲▼ ' if active else ''}{value}" + "\n", style="reverse bold" if active else "")
        t.append("─" * inner + "\n", style="dim")
        t.append(_fit(sample or "∅", inner), style="red" if _risky(cp) else "green" if cp.mode != "keep" else "")
        return t

    def _status(self) -> None:
        risky = [c for c in self.cols if _risky(self.plan.columns[c])]
        msg = ""
        if self.confirming:
            msg = f"[red b]⚠ {', '.join(risky)} will be exported with REAL values. enter again to confirm, any change to cancel.[/]"
        elif risky:
            msg = f"[red]⚠ real values kept in: {', '.join(risky)}[/]"
        self.query_one("#status", Static).update(msg)

    # ---------- actions ----------

    def action_move(self, step: int) -> None:
        self.idx = (self.idx + step) % len(self.cols)
        self.confirming = False
        self.refresh_cards()

    def action_switch_field(self) -> None:
        self.field = (self.field + 1) % len(FIELDS)
        self.refresh_cards()

    def action_cycle(self, step: int) -> None:
        col = self.cols[self.idx]
        cp = self.plan.columns[col]
        if FIELDS[self.field] == "role":
            role = ROLES[(ROLES.index(cp.role) + step) % len(ROLES)] if cp.role in ROLES else ROLES[0]
            set_column(self.plan, self.flat, col, role, default_mode(role))
        else:
            mode = MODES[(MODES.index(cp.mode) + step) % len(MODES)]
            set_column(self.plan, self.flat, col, cp.role, mode)
        self.confirming = False
        self.refresh_cards()

    def action_done(self) -> None:
        if any(_risky(cp) for cp in self.plan.columns.values()) and not self.confirming:
            self.confirming = True
            self._status()
            return
        self.exit(self.plan)

    def action_cancel(self) -> None:
        self.exit(None)


def _fit(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def edit_plan(flat: pd.DataFrame, plan: Plan, title: str = "") -> Plan | None:
    return ColumnEditor(flat, plan, title).run()
