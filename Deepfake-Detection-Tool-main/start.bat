@echo off
title DeepDetect Launcher
color 0A

echo.
echo  =============================================
echo   DeepDetect — Starting Services
echo  =============================================
echo.

REM ── Start Flask backend in a new window ──────────────────────────────────────
echo  [1/2] Starting Flask backend on http://localhost:5000 ...
start "DeepDetect Backend" cmd /k "chcp 65001 >nul && set PYTHONIOENCODING=utf-8 && cd /d "%~dp0backend" && python app.py"

REM ── Wait 3 seconds for Flask to boot ─────────────────────────────────────────
echo  Waiting for server to start...
timeout /t 3 /nobreak >nul

REM ── Verify Flask is responding before opening browser ────────────────────────
curl -s -o nul -w "%%{http_code}" http://localhost:5000/predict >nul 2>&1
if %errorlevel% neq 0 (
    echo  [INFO] Server may still be loading model — opening browser anyway...
)

REM ── Open frontend in default browser ─────────────────────────────────────────
echo  [2/2] Opening frontend in browser ...
start "" "%~dp0frontend\index.html"

echo.
echo  =============================================
echo   Done!
echo   Backend : http://localhost:5000
echo   Frontend: %~dp0frontend\index.html
echo.
echo   To stop: close the "DeepDetect Backend" window
echo  =============================================
echo.
pause
