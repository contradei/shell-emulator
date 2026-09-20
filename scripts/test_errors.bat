@echo off
setlocal
pushd "%~dp0.."
call run.bat --vfs vfs/several_files.xml --script scripts/error_unknown.txt <nul
if not errorlevel 1 exit /b 1
call run.bat --vfs vfs/several_files.xml --script scripts/error_quotes.txt <nul
if not errorlevel 1 exit /b 1
popd
exit /b 0
