@echo off
REM Start Study Companion at http://127.0.0.1:8000
REM   run.bat           start the server (sets things up on first run)
REM   run.bat rebuild   rebuild the frontend first (after changing frontend code)
setlocal
cd /d "%~dp0"
set PORT=8000

REM --- stop if something is already using the port
netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >nul
if not errorlevel 1 (
    echo Port %PORT% is already in use. Study Companion may already be running:
    echo   http://127.0.0.1:%PORT%
    start "" "http://127.0.0.1:%PORT%"
    pause
    exit /b 1
)

REM --- Python environment (first run only)
if not exist ".venv\Scripts\python.exe" (
    echo Creating Python environment...
    python -m venv .venv || goto :fail
    ".venv\Scripts\python" -m pip install -r backend\requirements.txt || goto :fail
    ".venv\Scripts\python" -m pip install -e D:\Y26\work_dir\LLM_Bridge || goto :fail
)

REM --- frontend build (first run, or "run.bat rebuild")
if /I "%~1"=="rebuild" if exist "frontend\dist" rmdir /s /q "frontend\dist"
if not exist "frontend\dist\index.html" (
    echo Building the frontend...
    pushd frontend
    if not exist "node_modules" (call npm install || (popd & goto :fail))
    call npm run build || (popd & goto :fail)
    popd
)

echo.
echo Study Companion is starting at http://127.0.0.1:%PORT%
echo Close this window or press Ctrl+C to stop it.
echo.
start "" "http://127.0.0.1:%PORT%"
".venv\Scripts\python" -m uvicorn backend.main:app --host 127.0.0.1 --port %PORT%
goto :eof

:fail
echo.
echo Setup failed. See the messages above.
pause
exit /b 1
