@echo off
setlocal
pushd "%~dp0.."
call run.bat --vfs vfs/several_files.xml --script scripts/error_unknown.txt <nul
if not errorlevel 1 exit /b 1
call run.bat --vfs vfs/several_files.xml --script scripts/error_quotes.txt <nul
if not errorlevel 1 exit /b 1
call run.bat --vfs vfs/several_files.xml --script scripts/error_missing_directory.txt <nul
if not errorlevel 1 exit /b 1
call run.bat --vfs vfs/several_files.xml --script scripts/error_not_directory.txt <nul
if not errorlevel 1 exit /b 1
call run.bat --vfs vfs/several_files.xml --script scripts/error_ls_arguments.txt <nul
if not errorlevel 1 exit /b 1
call run.bat --vfs vfs/several_files.xml --script scripts/error_missing_file.txt <nul
if not errorlevel 1 exit /b 1
call run.bat --vfs vfs/several_files.xml --script scripts/error_text_directory.txt <nul
if not errorlevel 1 exit /b 1
call run.bat --vfs vfs/several_files.xml --script scripts/error_head_arguments.txt <nul
if not errorlevel 1 exit /b 1
call run.bat --vfs vfs/several_files.xml --script scripts/error_tail_arguments.txt <nul
if not errorlevel 1 exit /b 1
call run.bat --vfs vfs/several_files.xml --script scripts/error_history_arguments.txt <nul
if not errorlevel 1 exit /b 1
call run.bat --vfs vfs/binary.xml --script scripts/error_binary.txt <nul
if not errorlevel 1 exit /b 1
call run.bat --vfs vfs/missing.xml <nul
if not errorlevel 1 exit /b 1
call run.bat --vfs vfs/invalid.xml <nul
if not errorlevel 1 exit /b 1
call run.bat --vfs vfs/invalid_base64.xml <nul
if not errorlevel 1 exit /b 1
popd
exit /b 0
