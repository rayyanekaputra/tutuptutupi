# Building the Windows exe

PyInstaller can't cross-compile, so the exe has to be built **on Windows**.
Result: one file, `dist\tutuptutupi.exe` (~100 MB, no Python needed on the user's PC).

## 1. One-time setup on the Windows PC
1. Install **Python 3.11+** from <https://www.python.org/downloads/windows/>
   (64-bit installer). Keep "py launcher" ticked; ticking "Add python.exe to PATH" is fine too.
2. Install **Git** from <https://git-scm.com/download/win> (or download the repo as a zip).
3. Open **PowerShell** / Windows Terminal and get the code:
   ```powershell
   git clone <your repo url> tutuptutupi
   cd tutuptutupi
   ```

## 2. Build
```powershell
powershell -ExecutionPolicy Bypass -File build_windows.ps1
```
The script creates `.venv`, installs the requirements + PyInstaller, runs the tests, then builds.
`-ExecutionPolicy Bypass` is needed because Windows blocks unsigned `.ps1` scripts by default;
it only applies to this one run.

First build takes a few minutes. Later builds: just run the same command again
(after `git pull`).

## 3. Test it
Data files are gitignored, so copy a spreadsheet to the Windows PC yourself. Then:
1. Put `dist\tutuptutupi.exe` in the same folder as the spreadsheet.
2. **Double-click** the exe. A terminal opens, the file picker lists the spreadsheets next to the exe.
3. Go through the flow. The column editor runs fullscreen on Windows (inline mode is Linux/macOS only); that's expected.
4. At the end the window says "press enter to close" so the result stays readable.

Also check from a terminal: `.\tutuptutupi.exe --version` and
`.\tutuptutupi.exe -y somefile.xlsx` (scripted mode, no pause at the end).

## 4. Shipping it
- Hand out just the `.exe`. Startup takes a few seconds (it unpacks itself to a temp folder each run).
- The exe is **unsigned**, so Windows will show **"Windows protected your PC"**.
  Tell users: click **More info → Run anyway**.
- If Defender flags or deletes it (false positives are common with PyInstaller exes),
  submit it at <https://www.microsoft.com/wdsi/filesubmission> as "incorrectly detected".
- Code signing (to reduce those warnings) is a later step.

## Troubleshooting
- `py` not found: reinstall Python with the py launcher, or replace `py -3` in the script with `python`.
- `ModuleNotFoundError` when running the exe: add `--hidden-import <module>` to the
  pyinstaller line in `build_windows.ps1` and rebuild.
- Weird characters / no colours: run it in Windows Terminal, not the old `cmd.exe` window.
  On Windows 11, Windows Terminal is the default.
