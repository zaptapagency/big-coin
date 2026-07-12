# MyCoin - Fully Automated Restart
# Run this with: powershell -ExecutionPolicy Bypass -File FULL_AUTO_RESTART.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " MyCoin - AUTOMATIC RESTART" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Kill Python processes
Write-Host "Step 1: Killing all Python processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Write-Host "✓ Processes killed" -ForegroundColor Green
Write-Host ""

# Step 2: Clear cache
Write-Host "Step 2: Clearing Python cache..." -ForegroundColor Yellow
$cacheDir = "C:\Users\usman\Desktop\BigCoinBB"
Get-ChildItem -Path $cacheDir -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $cacheDir -Recurse -Filter "*.pyc" | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Host "✓ Cache cleared" -ForegroundColor Green
Write-Host ""

# Step 3: Wait
Write-Host "Step 3: Waiting 3 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 3
Write-Host "✓ Ready to start" -ForegroundColor Green
Write-Host ""

# Step 4: Start servers
Write-Host "Step 4: Starting servers..." -ForegroundColor Yellow
Write-Host ""

$workDir = "C:\Users\usman\Desktop\BigCoinBB"

# Terminal 1: shared_state.py
Write-Host "  → Starting shared_state.py in new window..." -ForegroundColor Cyan
Start-Process -FilePath "cmd.exe" -ArgumentList "/k cd $workDir && python shared_state.py" -WindowStyle Normal
Start-Sleep -Seconds 2

# Terminal 2: web_app_shared.py
Write-Host "  → Starting web_app_shared.py in new window..." -ForegroundColor Cyan
Start-Process -FilePath "cmd.exe" -ArgumentList "/k cd $workDir && python web_app_shared.py" -WindowStyle Normal
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " ✓ Servers started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Wait for both terminals to show:"
Write-Host "     - Terminal 1: '[Shared State Server] Listening on 127.0.0.1:9999'"
Write-Host "     - Terminal 2: 'Running on http://127.0.0.1:5000'"
Write-Host "  2. Open browser: http://localhost:5000"
Write-Host "  3. Generate NEW address in Wallet tab"
Write-Host "  4. Try mining in Mining tab"
Write-Host ""
