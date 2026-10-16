# build dist\tutuptutupi.exe on windows. run from the repo folder:
#   powershell -ExecutionPolicy Bypass -File build_windows.ps1
$ErrorActionPreference = "Stop"

if (-not (Test-Path .venv)) { py -3 -m venv .venv }
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\pip install -r requirements-dev.txt

# tests first: no point shipping a broken exe
.venv\Scripts\pytest -q
if ($LASTEXITCODE -ne 0) { throw "tests failed" }

# textual/rich load some modules dynamically; pandas imports openpyxl/xlrd lazily
.venv\Scripts\pyinstaller --onefile --name tutuptutupi --paths . `
    --collect-submodules textual --collect-submodules rich `
    --hidden-import openpyxl --hidden-import xlrd `
    --specpath build --noconfirm tutuptutupi.py
if ($LASTEXITCODE -ne 0) { throw "pyinstaller failed" }

Write-Host "`ndone: dist\tutuptutupi.exe"
