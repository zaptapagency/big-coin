@echo off
REM BigCoin P2P Network - Fixed Launch Script
REM Fixes: JSON serialization issue with private keys

setlocal enabledelayedexpansion

cd C:\Users\usman\Desktop\BigCoinBB

echo.
echo ================================================================================
echo                    BigCoin P2P Network - FIXED Launch
echo ================================================================================
echo.

echo Fixes applied:
echo   ✓ Removed private key from JSON serialization
echo   ✓ Added proper error logging
echo   ✓ Improved exception handling
echo.

echo Step 1: Cleaning up...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 >nul

echo Step 2: Clearing cache...
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d" >nul 2>&1
)
echo   ✓ Ready

echo.
echo Step 3: Starting nodes...
echo.

start "BigCoin Node - Alice" cmd /k python node_rpc_server.py alice 9001 8001
timeout /t 3 >nul

start "BigCoin Node - Bob" cmd /k python node_rpc_server.py bob 9002 8002
timeout /t 3 >nul

start "BigCoin Node - Charlie" cmd /k python node_rpc_server.py charlie 9003 8003
timeout /t 3 >nul

echo   ✓ Nodes started

echo.
echo Step 4: Waiting for initialization...
timeout /t 5 >nul

echo Step 5: Connecting nodes...
python connect_nodes.py

echo.
echo ================================================================================
echo                         Network Ready!
echo ================================================================================
echo.
echo Access:
echo   Alice:   http://localhost:8001
echo   Bob:     http://localhost:8002
echo   Charlie: http://localhost:8003
echo.
echo All fixes applied. Ready to test!
echo.
pause
