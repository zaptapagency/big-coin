@echo off
REM ============================================================
REM  MoonBite instant miner (Windows one-click)
REM  Double-click this file, paste your address, and mine the
REM  live MoonBite chain. Needs Python 3 and moonbite-miner.py
REM  in the same folder.
REM ============================================================
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo  Python 3 is not installed or not on PATH.
  echo  Install it from https://www.python.org/downloads/  ^(tick "Add to PATH"^)
  echo.
  pause
  exit /b 1
)

if not exist "moonbite-miner.py" (
  echo.
  echo  moonbite-miner.py was not found next to this launcher.
  echo  Keep both files in the same folder.
  echo.
  pause
  exit /b 1
)

echo ============================================================
echo   MoonBite instant miner
echo ============================================================
echo.
set /p ADDR="Paste your MoonBite reward address (moon1... or M...): "
if "%ADDR%"=="" (
  echo  No address entered. Exiting.
  pause
  exit /b 1
)

echo.
echo  Starting miner. Press Ctrl+C to stop.
echo.
python moonbite-miner.py --address "%ADDR%"

echo.
pause
endlocal
