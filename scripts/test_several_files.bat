@echo off
setlocal
pushd "%~dp0.."
call run.bat --vfs vfs/minimal.xml <nul
if errorlevel 1 exit /b 1
call run.bat --script scripts/startup_basic.txt <nul
if errorlevel 1 exit /b 1
call run.bat --vfs vfs/several_files.xml --script startup.txt <nul
if errorlevel 1 exit /b 1
popd
exit /b 0
