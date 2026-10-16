"""entry point: interactive by default, flags for scripting."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="tutuptutupi", description="mask tabular data while keeping its shape")
    p.add_argument("file", nargs="?", help="input file (csv, tsv, xlsx, parquet, json, jsonl)")
    p.add_argument("-y", "--yes", action="store_true", help="non-interactive: accept detected roles and default modes")
    p.add_argument("-o", "--output", help="output file (non-interactive)")
    p.add_argument("--rows", type=int, default=20, help="rows to export (non-interactive, 0 = all)")
    p.add_argument("--index-col", action="append", default=[], help="index column (repeat for multiindex)")
    p.add_argument("--sheet", help="excel sheet name")
    p.add_argument("--id-width", type=int, default=8, help="fixed width for masked ids")
    p.add_argument("--seed", type=int, help="make masking reproducible")
    p.add_argument("--version", action="version", version=__version__)
    args = p.parse_args(argv)

    if not args.yes:
        from .app import run
        run(args.file, seed=args.seed)
        return

    from .core import auto_plan, mask_frame, sample_rows, schema_notes
    from .fileio import read_table, write_table

    if not args.file:
        p.error("--yes needs an input file")
    src = Path(args.file)
    df = read_table(src, args.sheet, args.index_col or None)
    plan = auto_plan(df, id_width=args.id_width, seed=args.seed)
    masked = mask_frame(sample_rows(df, args.rows or None, args.seed), plan)
    out = Path(args.output) if args.output else src.with_name(f"{src.stem}.masked{src.suffix}")
    if out.resolve() == src.resolve():
        p.error("refusing to overwrite the input file")
    write_table(masked, out)
    out.with_name(f"{out.stem}.schema.md").write_text(schema_notes(df, plan))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
