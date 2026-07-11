@echo off
rem Double-click to bring the DataVerse AI live site online.
rem Keep the window open during the demo; close it to go offline.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-live-backend.ps1"
pause
