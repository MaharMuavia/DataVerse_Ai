@echo off
REM DataVerse Analytics - Quick Startup Script
REM This batch file launches both the backend server and opens the dashboard

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   📊 DataVerse Analytics - Startup Script
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo    Please install Python 3.12+ from python.org
    pause
    exit /b 1
)

echo ✓ Python found
python --version

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   Server Startup
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

REM Check if backend is already running
echo Checking if backend is already running on port 8001...
netstat -ano | findstr ":8001" >nul 2>&1
if errorlevel 0 (
    echo ⚠️  Port 8001 appears to be in use
    echo    You can skip backend startup and proceed with the dashboard
)

echo.
echo Starting FastAPI Backend Server...
echo Location: %SCRIPT_DIR%dataverse_backend
echo Port: 8001
echo.
echo ℹ️  Backend will open in a new window
echo ℹ️  Keep this window open - it shows server logs
echo.

REM Start the backend in a new window
start "DataVerse Backend" cmd /k "cd /d "%SCRIPT_DIR%dataverse_backend" && python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --log-level info"

REM Wait for server to start
echo Waiting for backend to start...
timeout /t 3 /nobreak

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   Dashboard Launch
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

echo Opening dashboard in default browser...
echo Location: %SCRIPT_DIR%dashboard.html
echo.

REM Open the dashboard HTML file in default browser
start "" "%SCRIPT_DIR%dashboard.html"

echo.
echo ✓ Dashboard opened!
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   🚀 DataVerse Analytics is Ready!
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo   📈 Dashboard:   http://localhost:8001/docs
echo   🔌 Backend:     http://localhost:8001/api
echo   📊 Swagger UI:  http://localhost:8001/docs
echo.
echo   💡 Quick Tips:
echo      1. Go to Upload tab and select a CSV file
echo      2. Ask natural language questions in Query tab
echo      3. View results in real-time
echo      4. Check history tab to see all queries
echo.
echo   📖 Full docs:   See IMPLEMENTATION_GUIDE.md
echo   🧪 Test suite:  Run: python demo_client.py
echo.
echo   ℹ️  Backend window will remain open showing logs
echo   ℹ️  Close it only when you're done
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

pause
