@echo off
cd C:\Users\usman\Desktop\BigCoinBB
echo Starting MyCoin...
start cmd /k python shared_state.py
timeout /t 3 >/dev/null
start cmd /k python web_app_final.py
timeout /t 2 >/dev/null
start http://localhost:5002
