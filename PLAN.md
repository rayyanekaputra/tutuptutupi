# Implementation Plan

## UX — interactive flow
1. `tutuptutupi` (or `tutuptutupi path/to/file`) launches the app.
2. Pick file (path prompt with autocomplete) -> pick sheet (Excel) -> confirm index columns
   (single or multiple -> MultiIndex).
3. Show a `rich` table: each column with detected dtype, null %, sample **already masked**
   (raw values are never displayed).
4. Per column choose mode (default pre-selected): `partial` | `full` | `fake` | `keep`.
5. Choose row count to export (default: 20 rows) and output path/format.
6. Preview masked output -> confirm -> write.

## Masking modes
- **partial (default)**: keep ~50% of characters, replace the rest with `*`.
  - Strings: keep start and end, star the middle, spaces kept (`jason brody` -> `jas** ***dy`).
  - IDs/integers: deterministic positions starred, length kept (`34123` -> `**12*`).
    Output dtype becomes string; the original dtype is noted in a header/sidecar comment.
  - Dates: keep format, star some parts (`2024-03-15` -> `2024-**-**`).
  - Floats: keep sign, decimal places and magnitude (`1234.56` -> `1***.*6`).
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
- partial: output length == input length, about 50% starred, deterministic.
- fake: dtype preserved, consistent mapping, no input value in output.
- Date-format detection round trips.

## Notes
- Partial masking still reveals part of each value. Fine for an LLM's eyes, not for public release.
  Mention this in the README and the app.
