@echo off
REM MoonBite one-click CPU miner (Windows).
REM Prompts for your reward address + node RPC details, then mines.

setlocal enabledelayedexpansion
title MoonBite CPU Miner

echo ================================================================
echo   MoonBite CPU Miner
echo ================================================================
echo.

REM --- Reward address ---
if "%MINE_ADDRESS%"=="" (
  set /p MINE_ADDRESS="Your MoonBite reward address (moon1... or M...): "
)
if "%MINE_ADDRESS%"=="" (
  echo No address entered. Exiting.
  pause
  exit /b 1
)

REM --- RPC connection (press Enter for local-node defaults) ---
if "%BIGCOIN_RPC_HOST%"=="" set /p BIGCOIN_RPC_HOST="Node RPC host [127.0.0.1]: "
if "%BIGCOIN_RPC_HOST%"=="" set BIGCOIN_RPC_HOST=127.0.0.1

if "%BIGCOIN_RPC_PORT%"=="" set /p BIGCOIN_RPC_PORT="Node RPC port [9445]: "
if "%BIGCOIN_RPC_PORT%"=="" set BIGCOIN_RPC_PORT=9445

if "%BIGCOIN_RPC_USER%"=="" set /p BIGCOIN_RPC_USER="RPC username: "
if "%BIGCOIN_RPC_PASSWORD%"=="" set /p BIGCOIN_RPC_PASSWORD="RPC password: "

echo.
echo Starting miner -> %BIGCOIN_RPC_HOST%:%BIGCOIN_RPC_PORT%  reward %MINE_ADDRESS%
echo Press Ctrl+C to stop.
echo.

python "%~dp0moonbite_miner.py" --address "%MINE_ADDRESS%"
if errorlevel 1 (
  echo.
  echo Miner exited with an error. Check the node is running and the RPC details are correct.
)
pause
