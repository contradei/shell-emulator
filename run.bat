@echo off
setlocal
pushd "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m src.shell_emulator.main %*
) else (
    where py >nul 2>nul
    if errorlevel 1 (
        python -m src.shell_emulator.main %*
    ) else (
        py -3 -m src.shell_emulator.main %*
    )
)
set "result=%errorlevel%"
popd
exit /b %result%
