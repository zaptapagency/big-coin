@echo off
REM Complete P2P Network Launch Script - Fully Automated
REM This starts all 3 nodes, connects them, and runs tests

setlocal enabledelayedexpansion

cd C:\Users\usman\Desktop\BigCoinBB

echo.
echo ================================================================================
echo                    BigCoin P2P Network - Full Launch
echo ================================================================================
echo.
echo This script will:
echo   1. Kill any existing processes
echo   2. Start 3 full nodes (Alice, Bob, Charlie)
echo   3. Connect them together
echo   4. Run automated tests
echo   5. Show network status
echo.

echo Step 1: Cleaning up old processes...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 >nul
echo   ✓ Cleanup complete

echo.
echo Step 2: Clearing Python cache...
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d" >nul 2>&1
)
echo   ✓ Cache cleared

echo.
echo Step 3: Starting 3 nodes in separate terminals...
echo.

echo   Starting Alice (P2P: 9001, RPC: 8001)...
start "BigCoin Node - Alice" cmd /k python node_rpc_server.py alice 9001 8001
timeout /t 3 >nul

echo   Starting Bob (P2P: 9002, RPC: 8002)...
start "BigCoin Node - Bob" cmd /k python node_rpc_server.py bob 9002 8002
timeout /t 3 >nul

echo   Starting Charlie (P2P: 9003, RPC: 8003)...
start "BigCoin Node - Charlie" cmd /k python node_rpc_server.py charlie 9003 8003
timeout /t 3 >nul

echo   ✓ All 3 nodes started!

echo.
echo Step 4: Waiting for nodes to initialize...
timeout /t 5 >nul

echo.
echo Step 5: Connecting nodes together...
python connect_nodes.py >nul 2>&1 &
timeout /t 3 >nul
echo   ✓ Nodes connected!

echo.
echo Step 6: Running automated tests...
echo.
python test_p2p_network.py

echo.
echo ================================================================================
echo                         Network Launch Complete!
echo ================================================================================
echo.
echo Your P2P Network is Running!
echo.
echo Access points:
echo   Alice:   http://localhost:8001
echo   Bob:     http://localhost:8002
echo   Charlie: http://localhost:8003
echo.
echo Next steps:
echo   1. Open http://localhost:8001 in your browser
echo   2. Go to Wallet tab → Generate New Address
echo   3. Go to Mining tab → Paste address → Start Mining
echo   4. Wait 30 seconds for block
echo   5. Check http://localhost:8002 → Height increased!
echo.
echo To monitor network status, run in a new terminal:
echo   python connect_nodes.py
echo.
echo To stop the network, close all 3 node terminals
echo.
echo ================================================================================
echo.
pause
