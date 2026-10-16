# tutuptutupi

an interactive cli that **masks tabular data while keeping its shape**.

use it when you want to show a spreadsheet to an llm (or load it into a test environment)
but the real values must not leave your machine. the output keeps the columns, dtypes,
index, nulls and value formats, so whoever reads it still understands the structure.

```
item code   item name       created date   price
**n1****    fro**n a****    2026-**-**     52144.06
```

> ⚠ partial masking still shows part of each value. it is fine for an llm's eyes,
> **not** for public release. use `full` or `fake` mode when that matters.

## what it keeps

- row/column counts, column names and order
- index structure (single index or multiindex, names, levels)
- dtypes (int stays int, float stays float, bool, datetime, category, string)
- value format: date format, string length and character pattern (`ab-1234` -> `xq-8302`)
- null positions
- repeated values map to the same masked value, so joins and groupbys still work

## what it hides

- by default about half of each value is replaced with `*` (`jason brody` -> `jas** ***dy`)
- ids are masked to a fixed width (default 8), so the real length is hidden (`34123` -> `**12****`)
- plain numbers (amounts, counts) are kept unless you mark the column as `id` or pick `fake`
- no network calls, no logs of real values, the masking key lives only in memory for one run

## install

needs python 3.11+.

```sh
git clone <repo url> tutuptutupi
cd tutuptutupi
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

on windows there is also a single `.exe` build, see [build_windows.md](BUILD_WINDOWS.md).

## guide

### 1. start the app

```sh
python3 tutuptutupi.py            # pick a file from a list
./tutuptutupi.py path/to/file.xlsx  # or pass the file directly
```

the script switches to `.venv` by itself, no need to activate it.
on windows, put `tutuptutupi.exe` next to your spreadsheet and double-click it.

supported files: `.csv`, `.tsv`, `.xlsx`, `.xlsm`, `.xls`, `.parquet`, `.json`, `.jsonl`.

### 2. walk through the steps

every screen shows a header like `✦ step 2/6 · pick a file ✦` and a dim `now: … / next: …`
note at the bottom, so you always know where you are.

1. **language** — english (default) or bahasa indonesia. skip it with `--lang en` or `--lang id`.
2. **pick a file** — arrow keys to move, type to filter, enter to choose.
   the list shows supported files in the app's folder, newest first, with size and age.
   files somewhere else: choose `✎ type a path…`. for excel files you also pick the sheet.
3. **index columns** — pick which columns form the index (or none).
   `←/→` move, `space` toggles, `enter` confirms. picking several makes a multiindex;
   the order you toggle them in is the level order.
4. **mask columns** — the column editor. each column is a card with its dtype, role, mode
   and one masked sample value that updates live.
   - `←/→` move between columns
   - `tab` switch between role and mode
   - `↑/↓` change the value
   - `enter` done, `esc` cancel

   the app guesses a role for every column, so often you only need to fix a few.
   choosing `keep` on an id or text column asks for confirmation.
5. **rows & preview** — how many rows to export (default 20) and a preview of the masked output.
6. **save** — choose the output path. by default it is saved next to the input as
   `<name>.masked.<ext>`, plus a `<name>.masked.schema.md` file.

### 3. give it to the llm

share the `.masked` file **and** the `.schema.md` sidecar. the sidecar lists each column's
original dtype, role and mode, so the llm knows that, for example, a masked id was an int.

## roles and modes

**roles** describe what a column is:

| role       | meaning                                  |
|------------|------------------------------------------|
| `id`       | identifiers, codes, keys                 |
| `text`     | names, free text, emails                 |
| `number`   | amounts, counts, measurements            |
| `date`     | dates and datetimes                      |
| `category` | small set of repeating labels            |
| `bool`     | true/false                               |

**modes** decide how a column is masked:

| mode      | what it does                                                          | example                    |
|-----------|-----------------------------------------------------------------------|----------------------------|
| `partial` | default. keeps ~50% of characters, stars the rest                     | `jason brody` -> `jas** ***dy` |
| `full`    | every character becomes `*`, length and punctuation stay              | `ab-1234` -> `**-****`     |
| `fake`    | consistent fake value with the same type and pattern                  | `ab-1234` -> `xq-8302`     |
| `keep`    | leave the column as it is (default for plain numbers)                 | `52144.06` -> `52144.06`   |

ids in `partial` mode always come out at the fixed width (`--id-width`, default 8)
and become strings; the original dtype is noted in the sidecar.

## scripted use

skip the prompts with `--yes`: detected roles and default modes are used as they are.

```sh
./tutuptutupi.py sales.csv --yes                       # writes sales.masked.csv
./tutuptutupi.py report.xlsx --yes --sheet q3 --rows 50 -o out.xlsx
./tutuptutupi.py orders.parquet --yes --index-col region --index-col order_id
```

| flag              | what it does                                         |
|-------------------|------------------------------------------------------|
| `file`            | input file                                           |
| `-y`, `--yes`     | non-interactive, accept the detected plan            |
| `-o`, `--output`  | output file (default `<name>.masked.<ext>`)          |
| `--rows n`        | rows to export (default 20, `0` = all)               |
| `--index-col col` | index column, repeat for a multiindex                |
| `--sheet name`    | excel sheet                                          |
| `--id-width n`    | fixed width for masked ids (default 8)               |
| `--seed n`        | make the masking reproducible across runs            |
| `--lang en\|id`   | ui language, skips the language prompt               |
| `--version`       | print the version                                    |

the app refuses to overwrite the input file.

## development

```sh
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/pytest -q
```

project notes for contributors live in [agents.md](AGENTS.md) and [plan.md](PLAN.md).
