@echo off
REM MyCoin Mining - One-Click Restart & Start
REM This script kills old processes, clears cache, and starts fresh servers

setlocal enabledelayedexpansion

echo.
echo ================================================================
echo   MyCoin Mining - One-Click Auto Restart
echo ================================================================
echo.
echo Fixing: "Failed to start mining" error
echo Method: Clear bytecode cache and restart servers
echo.

REM Kill all Python processes
echo [Step 1/5] Killing old Python processes...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 >nul
echo   ✓ Done
echo.

REM Clear __pycache__ directories
echo [Step 2/5] Clearing Python cache directories...
for /d /r "C:\Users\usman\Desktop\BigCoinBB" %%d in (__pycache__) do (
    if exist "%%d" (
        rmdir /s /q "%%d" >nul 2>&1
    )
)
echo   ✓ Done
echo.

REM Delete .pyc files
echo [Step 3/5] Clearing compiled Python files (.pyc)...
for /r "C:\Users\usman\Desktop\BigCoinBB" %%f in (*.pyc) do (
    del "%%f" >nul 2>&1
)
echo   ✓ Done
echo.

REM Wait
echo [Step 4/5] Waiting 3 seconds...
timeout /t 3 >nul
echo   ✓ Ready
echo.

REM Start servers
echo [Step 5/5] Starting servers...
echo.

cd C:\Users\usman\Desktop\BigCoinBB

echo   Opening Terminal 1: shared_state.py
start cmd /k python shared_state.py
timeout /t 2 >nul

echo   Opening Terminal 2: web_app_shared.py
start cmd /k python web_app_shared.py
timeout /t 2 >nul

echo.
echo ================================================================
echo   ✓ SERVERS STARTING!
echo ================================================================
echo.
echo What to do now:
echo   1. Wait for BOTH terminals to show green text
echo   2. Terminal 1: "[Shared State Server] Listening on 127.0.0.1:9999"
echo   3. Terminal 2: "Running on http://127.0.0.1:5000"
echo   4. Then open browser: http://localhost:5000
echo   5. Go to Wallet tab → "Generate New Address"
echo   6. Go to Mining tab → Paste address → Click "Start Mining"
echo.
echo Expected: Progress bar updates, mining completes, no errors!
echo.
pause
