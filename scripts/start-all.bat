@echo off
REM Start DataVerse AI - Backend & Frontend
REM This batch file automatically starts both servers

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "WORK_DIR=%%~fI"
cd /d "%WORK_DIR%"

REM Activate Python venv and start backend and frontend
powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%start-all.ps1"

pause
