#!/usr/bin/env python3
"""start the app: `python tutuptutupi.py` or `./tutuptutupi.py [file]` (or the windows exe)."""

import os
import subprocess
import sys
import traceback
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)  # running as a pyinstaller exe
HERE = Path(__file__).resolve().parent
VENV_PY = HERE / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

if not FROZEN:
    try:
        import pandas, questionary, rich  # noqa: F401,E401
    except ImportError:
        # deps missing in this python: rerun with the project's venv if it exists
        if VENV_PY.exists() and Path(sys.prefix).resolve() != (HERE / ".venv").resolve():
            if os.name == "nt":  # execv on windows detaches from the console
                sys.exit(subprocess.call([str(VENV_PY), __file__, *sys.argv[1:]]))
            os.execv(VENV_PY, [str(VENV_PY), __file__, *sys.argv[1:]])
        sys.exit("missing dependencies. run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt")

sys.path.insert(0, str(HERE))
from cli import main  # noqa: E402
from i18n import t  # noqa: E402


def main_keep_open() -> None:
    """double-clicked exe: the console window closes on exit, so wait for enter first."""
    try:
        main()
    except SystemExit as e:
        if isinstance(e.code, str):
            print(e.code, file=sys.stderr)
    except KeyboardInterrupt:
        pass
    except Exception:  # noqa: BLE001 - show the error instead of a vanishing window
        traceback.print_exc()
    try:
        input(f"\n{t('press_enter')}")
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    # --yes is scripted use from a terminal: no pause there
    if FROZEN and not {"-y", "--yes"} & set(sys.argv[1:]):
        main_keep_open()
    else:
        main()
