# Implementation Plan

## UX — interactive flow
1. `tutuptutupi` (or `tutuptutupi path/to/file`) launches the app.
2. Pick file (path prompt with autocomplete) -> pick sheet (Excel) -> confirm index columns
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
- `io.py` — read/write CSV, TSV, Excel, Parquet, JSON.
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
