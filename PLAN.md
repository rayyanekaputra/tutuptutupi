# Implementation Plan

## UX — interactive flow
1. `tutuptutupi` (or `tutuptutupi path/to/file`) launches the app.
2. Pick file (arrow-key list) -> pick sheet (Excel) -> pick index columns on horizontal cards
   (same look as the column editor; toggle order = multiindex level order)
   (single or multiple -> MultiIndex).
3. Show a `rich` overview table: each column with detected dtype and null % (no raw values).
4. **Iterate column by column.** For each column ask its role (detected guess pre-selected):
   `id` | `name/text` | `number` | `date` | `category` | `bool`.
   Then ask the mode (default depends on role). Numeric columns are only censored if
   marked `id` — plain numbers (amounts, counts, measurements) default to `keep`.
5. Choose row count to export (default: 20 rows) and output path/format.
6. Preview masked output -> confirm -> write.

## Masking modes
- **partial (default)**: keep ~50% of characters, replace the rest with `*`.
  - Strings: keep start and end, star the middle, spaces kept (`jason brody` -> `jas** ***dy`).
  - IDs: always padded/truncated to a **fixed width (default 8, configurable)** so the real
    length is hidden; a few real digits stay visible (`34123` -> `**12****`).
    Output dtype becomes string; the original dtype is noted in a sidecar/header comment.
  - Dates: keep format, star some parts (`2024-03-15` -> `2024-**-**`).
  - Plain numbers (not IDs): default `keep`; user may choose `fake` to keep dtype & magnitude.
- **full**: replace every character with `*` (keeps length and punctuation).
- **fake**: HMAC-keyed replacement that keeps the same type and pattern (`AB-1234` -> `XQ-8302`,
  int stays int, date stays date). Same input -> same output within a run.
- **keep**: leave the column as-is (requires explicit choice and confirmation).
- Nulls stay null in all modes. Column/index names kept unless the user asks to mask them.

## Modules
- `fileio.py` — read/write CSV, TSV, Excel, Parquet, JSON.
- `detect.py` — infer per column kind: id, name/text, email, date string + format, number, bool, category.
- `maskers.py` — pure functions per mode x kind.
- `core.py` — `mask_frame(df, plan) -> DataFrame`, including index levels.
- `app.py` — interactive flow (questionary + rich).
- `cli.py` — entry point; flags (`--mode`, `--rows`, `-o`, `--yes`) for non-interactive runs.

## Tests
- Shape, index structure, null positions preserved in every mode.
- partial: names keep length, about 50% starred, deterministic.
- IDs: output always equals the fixed width regardless of input length.
- Non-ID numeric columns untouched by default.
- fake: dtype preserved, consistent mapping, no input value in output.
- Date-format detection round trips.

## Notes
- Partial masking still reveals part of each value. Fine for an LLM's eyes, not for public release.
  Mention this in the README and the app.

## Phase 1.1 — arrow-key file picker (done)
Goal: no typing paths on first run. Running `./tutuptutupi.py` with no file shows a menu.

```
? file to mask:
❯ Item Cost and Selling Price Latest  - 2026-10-12T152407.896.xls   (1.3 MB, 4 days ago)
  sales_2025.csv                                                    (220 KB, today)
  ✎ type a path…
```

Rules:
- Always lists the **project folder** (where `tutuptutupi.py` lives), not the shell's cwd.
- **Only that folder**: no subfolders listed, no folder navigation. Files elsewhere go
  through `✎ type a path…` (current path prompt with autocomplete).
- Only supported extensions (`fileio.SUPPORTED`), sorted newest first.
- Each entry shows file size and modified age.
- Hide our own outputs: `*.masked.*` and `*.schema.md`.
- Type-to-filter when the list is long (questionary `select` with `use_search_filter`, or
  `autocomplete` fallback if the installed version lacks it).
- No supported files found -> say so and go straight to `type a path…`.
- A file passed on the command line skips the picker (unchanged).
- Default save location stays next to the input file.

Implementation:
- `app.py`: new `_list_files(folder) -> list[Path]` (pure, testable) and
  `_pick_file()` rewritten to use `questionary.select`.
- Project folder resolved from `Path(__file__).parent` of the modules.
- Helper `_human_size()`, `_age()` for the labels.

Tests:
- `_list_files` returns only supported, non-masked files, newest first, no directories.

## Phase 1.2 — only ask about chosen columns (done, used as fallback)
Problem: after answering one column the app walks through every remaining column.

New flow:
1. Show a summary table of all columns: name, dtype, guessed role, default mode,
   one masked sample value.
2. `questionary.checkbox("which columns do you want to change?")` (none = accept all).
3. Ask role + mode **only for the ticked columns**. Unticked keep their guesses.
4. Show the summary again with the changes; confirm or edit again.

Implementation: in `app.py`, replace the per-column loop with
`_summary_table(plan, sample_row)` + `_edit_columns(plan, cols)`.

## Phase 2 — horizontal column editor (Textual) (done)
Spreadsheet-like screen to set every column's role/mode in one place.

```
 tutuptutupi — Item Cost...xls  (4066 rows)     ←/→ column  ↑/↓ change  tab role/mode  enter done
┌────────────┬────────────┬────────────┬──────────────┬────────────┬──────┐
│ Item Code  │ Item Name  │ Price List │ Created Date │ Latest HPP │ …    │
│ str        │ str        │ str        │ datetime     │ float      │      │
├────────────┼────────────┼────────────┼──────────────┼────────────┼──────┤
│ role: id   │ text       │ category   │ date         │ number     │      │
│ mode: part │ partial    │ partial    │ partial      │ keep       │      │
├────────────┼────────────┼────────────┼──────────────┼────────────┼──────┤
│ **N1****   │ Frozen A** │ Pric* **** │ 2026-**-**   │ 52144.06   │      │
└────────────┴────────────┴────────────┴──────────────┴────────────┴──────┘
```

Rules:
- One **sample row** only, always shown masked, updated live when a mode changes.
  Prefer a row with the fewest nulls so every column shows something.
- ←/→ move between columns, horizontal scroll when they don't fit.
  ↑/↓ cycle the value, tab switches between role and mode, enter confirms, esc cancels.
- `keep` on an id/text column still asks for confirmation.
- Fallback to the Phase 1.2 checkbox flow if Textual can't start (too narrow / no tty).
- Rest of the flow (file picker, rows, save) stays as is.

Implementation:
- New `editor.py`: `ColumnEditor(App)` takes `(columns, plan, sample_row)` and returns the
  edited `Plan` (or `None` on cancel). No file I/O inside.
- Add `textual` to dependencies.
- Tests: Textual `run_test()` pilot — press keys, assert resulting plan; sample cell never
  shows the raw value for masked modes.
