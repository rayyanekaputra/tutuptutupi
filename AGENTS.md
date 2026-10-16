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
  (e.g. `AB-1234` -> `XQ-8302`), number of digits/decimals, sign (except IDs, see below)
- Nulls: same positions stay null
- Cardinality, roughly (repeated values map to the same fake value -> joins/groupbys still work)

## What must be hidden
- Default mode is **partial masking**: about half of each value is replaced with `*`
  (e.g. `jason brody` -> `jas** ***dy`). IDs are masked to a **fixed width**
  (default 8) so the real length is hidden: `34123` -> `**12****`. The LLM can still tell
  what kind of data it is. Full masking / synthetic fakes are opt-in modes.
- Only columns the user marks as `id` get censored among numeric columns; plain numbers
  (amounts, counts) are kept by default. The app asks the role of each column one by one.
- Output must always contain data. No schema-only or empty output.

## Principles
- Deterministic per run with an optional `--seed`; consistent mapping within a run.
- Use a keyed hash (HMAC with a random per-run key) for value->fake mapping.
  Never store the key or the mapping on disk.
- No network calls. No logging of real values.
- Keep it simple: one package, few dependencies (pandas, optionally pyarrow/openpyxl).

## Stack & conventions
- Python 3.11+, pandas. Interactive UI via `questionary` (prompts), `rich` (tables) and `textual` (index picker + horizontal column editor, `editor.py`).
  The textual apps run **inline** (`run(inline=True)`, `ansi_color=True`) like agentic CLIs, not fullscreen; keep it that way. (Textual itself falls back to fullscreen on Windows.)
  A non-interactive path (flags) may exist for scripting, but interactive is the main UX.
- UI language: the first prompt picks English (default) or Bahasa Indonesia (`--lang en|id` skips it).
  All user-facing strings live in `i18n.py` (`t(key)`, every key needs both languages); role/mode names
  and the `.schema.md` sidecar stay English.
- Every step starts with a lowercase decorated header (`✦ step n/6 · title ✦`, file name as a yellow badge)
  and every prompt/TUI shows a dim `now: … / next: …` note at the bottom (`_step()` / `_with_note()` in `app.py`).
  New prompts go through `_ask()` so they get the note; new steps need `STEPS` + `s_/now_/next_` keys in `i18n.py`.
- Setup: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` (add `-r requirements-dev.txt` for tests). Run app: `python3 tutuptutupi.py` (or `./tutuptutupi.py [file]`) — it switches to `.venv` automatically.
- Tests with `pytest`. Run: `.venv/bin/pytest -q`.
- Windows exe: PyInstaller onefile, built on Windows with `build_windows.ps1` (steps in `BUILD_WINDOWS.md`).
  When frozen, the file picker lists the exe's folder and the window waits for enter before closing (`tutuptutupi.py`).
- Each export also writes `<name>.schema.md` with original dtypes/roles for the llm.
- Layout: entry point `tutuptutupi.py`, flat modules in the repo root (`app.py`, `cli.py`, `core.py`, `detect.py`, `editor.py`, `fileio.py`, `i18n.py`, `maskers.py`), `tests/`, `PLAN.md`. No nested package folder.
- Type hints everywhere; small pure functions per dtype.
- Any new or changed dependency goes in `requirements.txt` (runtime) or `requirements-dev.txt` (tests) **and** `pyproject.toml`, pinned to the installed version.

## Git workflow
- Commit after **every** update (code, docs, config). One logical change per commit.
- After each commit, keep the context files current: if the change affects anything CLAUDE.md or
  AGENTS.md describe (stack, layout, modules, UX, rules, commands), update them in a follow-up
  `docs` commit (e.g. `docs(agents): note inline tui`). Skip it when nothing they say changed.
- Commit messages are **entirely lowercase, including trailers** (e.g. `co-authored-by: claude opus 5.5 <noreply@anthropic.com>`), conventional-commit style:
  `type(scope): short summary`, e.g. `feat: add id masker`, `docs(agents): add git rules`,
  `fix(io): keep multiindex on csv read`, `test: cover fixed-width ids`, `chore: add gitignore`.
- Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`. Scope is optional.
