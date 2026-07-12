@echo off
echo.
echo ========================================
echo  MyCoin - CLEAN RESTART (Clear Cache)
echo ========================================
echo.

echo Step 1: Kill all Python processes...
taskkill /F /IM python.exe 2>nul
echo   ✓ Killed old processes
echo.

echo Step 2: Clear Python cache (__pycache__)...
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" (
        rmdir /s /q "%%d" 2>nul
        echo   ✓ Cleared %%d
    )
)
echo   ✓ Cache cleared
echo.

echo Step 3: Delete .pyc files...
for /r . %%f in (*.pyc) do (
    del "%%f" 2>nul
)
echo   ✓ .pyc files deleted
echo.

echo Step 4: Wait 3 seconds...
timeout /t 3 /nobreak
echo.

echo ========================================
echo NEXT: Open 2 NEW Command Prompts
echo ========================================
echo.
echo Copy and paste this into FIRST terminal:
echo   cd C:\Users\usman\Desktop\BigCoinBB
echo   python shared_state.py
echo.
echo Copy and paste this into SECOND terminal:
echo   cd C:\Users\usman\Desktop\BigCoinBB
echo   python web_app_shared.py
echo.
echo Then refresh browser: http://localhost:5000
echo.
pause
