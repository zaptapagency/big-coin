@echo off
echo.
echo ========================================
echo  MyCoin - RESTART ALL SERVERS
echo ========================================
echo.
echo Step 1: Kill all Python processes
taskkill /F /IM python.exe 2>nul
echo   (killed old processes)
echo.
echo Step 2: Wait 3 seconds...
timeout /t 3 /nobreak
echo.
echo Step 3: Instructions for manual restart:
echo.
echo   Open 3 NEW Command Prompts:
echo.
echo   === TERMINAL 1 ===
echo   cd C:\Users\usman\Desktop\BigCoinBB
echo   python shared_state.py
echo.
echo   === TERMINAL 2 ===
echo   cd C:\Users\usman\Desktop\BigCoinBB
echo   python web_app_shared.py
echo.
echo   === TERMINAL 3 ===
echo   Open browser: http://localhost:5000
echo.
echo ========================================
echo.
pause
