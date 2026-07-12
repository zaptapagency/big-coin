@echo off
REM Start a 3-node BigCoin P2P network for testing

setlocal enabledelayedexpansion

cd C:\Users\usman\Desktop\BigCoinBB

echo.
echo ================================================
echo  BigCoin P2P Network - Start 3 Nodes
echo ================================================
echo.

REM Node 1: Alice
echo Starting Node 1 (Alice) on port 9001 (RPC: 8001)...
start "BigCoin Node 1 - Alice" cmd /k python node_rpc_server.py alice 9001 8001

timeout /t 3 >nul

REM Node 2: Bob
echo Starting Node 2 (Bob) on port 9002 (RPC: 8002)...
start "BigCoin Node 2 - Bob" cmd /k python node_rpc_server.py bob 9002 8002

timeout /t 3 >nul

REM Node 3: Charlie
echo Starting Node 3 (Charlie) on port 9003 (RPC: 8003)...
start "BigCoin Node 3 - Charlie" cmd /k python node_rpc_server.py charlie 9003 8003

timeout /t 3 >nul

echo.
echo ================================================
echo  Nodes Started!
echo ================================================
echo.
echo Alice:   P2P: localhost:9001  RPC: http://localhost:8001
echo Bob:     P2P: localhost:9002  RPC: http://localhost:8002
echo Charlie: P2P: localhost:9003  RPC: http://localhost:8003
echo.
echo Next: Run CONNECT_NODES.bat to connect them
echo.
pause
