# AGENTS.md — tutuptutupi

## What this is
An **interactive** Python CLI app that **masks tabular data while preserving its shape**, so the
output can be shared safely with LLMs or staged into test environments.
The consumer only needs structure, not real values.

## What must be preserved
- Row/column counts, column names, column order
- Index structure (single vs MultiIndex, index names, levels)
- dtypes (int stays int, float stays float, bool, datetime, category, string)
- Value *format*: date format string, string length/char class pattern
  (e.g. `AB-1234` -> `XQ-8302`), number of digits/decimals, sign
- Nulls: same positions stay null
- Cardinality, roughly (repeated values map to the same fake value -> joins/groupbys still work)

## What must be hidden
- Default mode is **partial masking**: about half of each value is replaced with `*`
  (e.g. `jason brody` -> `jas*******y`, `34123` -> `**12*`), so the LLM can still tell
  what kind of data it is. Full masking / synthetic fakes are opt-in modes.
- Output must always contain data. No schema-only or empty output.

## Principles
- Deterministic per run with an optional `--seed`; consistent mapping within a run.
- Use a keyed hash (HMAC with a random per-run key) for value->fake mapping.
  Never store the key or the mapping on disk.
- No network calls. No logging of real values.
- Keep it simple: one package, few dependencies (pandas, optionally pyarrow/openpyxl).

## Stack & conventions
- Python 3.11+, pandas. Interactive UI via `questionary` (prompts) + `rich` (tables/preview).
  A non-interactive path (flags) may exist for scripting, but interactive is the main UX.
- Tests with `pytest`. Run: `pytest -q`.
- Layout: `tutuptutupi/` (package), `tests/`, `PLAN.md` (implementation plan).
- Type hints everywhere; small pure functions per dtype.
