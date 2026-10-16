#!/usr/bin/env python3
"""start the app: `python tutuptutupi.py` or `./tutuptutupi.py [file]`."""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV_PY = HERE / ".venv" / "bin" / "python"

try:
    import pandas, questionary, rich  # noqa: F401,E401
except ImportError:
    # deps missing in this python: rerun with the project's venv if it exists
    if VENV_PY.exists() and Path(sys.prefix).resolve() != (HERE / ".venv").resolve():
        os.execv(VENV_PY, [str(VENV_PY), __file__, *sys.argv[1:]])
    sys.exit("missing dependencies. run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt")

sys.path.insert(0, str(HERE))
from cli import main  # noqa: E402

if __name__ == "__main__":
    main()
