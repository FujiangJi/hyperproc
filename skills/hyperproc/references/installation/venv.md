# Existing Python with venv

A virtual environment is suitable when Python 3.12 and required scientific wheels are available. It does not supply system compilers or ISOFIT assets.

POSIX shell:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install "hyperproc==0.1.2"
python -m pip check
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install "hyperproc==0.1.2"
.\.venv\Scripts\python.exe -m pip check
```

Using the explicit environment interpreter avoids changing PowerShell execution policy solely to activate a script. If activation is desired, PowerShell uses `.\.venv\Scripts\Activate.ps1`; cmd.exe uses `.venv\Scripts\activate.bat`. Do not assume `py -3.12` exists or a requested interpreter is installed: inspect first.

For a released package use PyPI with the selected version. `python -m pip install -e .` is an editable checkout installation and is appropriate only for a requested development environment; it is not automatically the released wheel. Always record package version and imported path.

Add only needed [extras](capabilities.md). If a compiled dependency build fails, use supported wheels/compatible conda or diagnose the actual library/toolchain; do not casually mix architecture/library providers. Atmospheric tasks still need [external tools/assets](atmos-assets.md), and this skill's native Windows atmospheric route uses WSL2.

Official mechanics: [Python venv documentation](https://docs.python.org/3/library/venv.html).
