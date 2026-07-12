@echo off
REM MyCoin Web Dashboard - Simple Launcher

setlocal enabledelayedexpansion

cd C:\Users\usman\Desktop\BigCoinBB

echo.
echo ========================================
echo   MyCoin Web Dashboard
echo ========================================
echo.

echo Killing old processes...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 >nul

echo Clearing cache...
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d" >nul 2>&1
)

echo Starting server...
start cmd /k python shared_state.py
timeout /t 3 >nul

start cmd /k python web_app_shared.py
timeout /t 2 >nul

echo.
echo ========================================
echo Opening browser...
echo ========================================
echo.

start http://localhost:5000

timeout /t 2 >nul
echo Browser opening at: http://localhost:5000
echo.
echo Use the dashboard to:
echo   1. Wallet tab: Generate address
echo   2. Mining tab: Paste address and mine
echo   3. Blockchain tab: View results
echo.
echo Close this window to stop.
pause
