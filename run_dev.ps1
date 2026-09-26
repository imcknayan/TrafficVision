# TrafficVision AI - Multi-Service Local Launcher
Write-Host "Starting TrafficVision AI Services..." -ForegroundColor Cyan

# 1. Start Auth Service on port 8001
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting Auth Service on :8001...' -ForegroundColor Green; python -m uvicorn app.main:app --app-dir services/auth --port 8001 --reload"

# 2. Start Route Analysis Service on port 8004
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting Route Analysis Service on :8004...' -ForegroundColor Green; python -m uvicorn app.main:app --app-dir services/route-analysis --port 8004 --reload"

Start-Sleep -Seconds 2

# 3. Start API Gateway on port 8000
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting API Gateway on :8000...' -ForegroundColor Green; $env:AUTH_SERVICE_URL='http://127.0.0.1:8001'; $env:ROUTE_ANALYSIS_SERVICE_URL='http://127.0.0.1:8004'; python -m uvicorn app.main:app --app-dir services/gateway --port 8000 --reload"

Write-Host "All 3 services launched!" -ForegroundColor Green
Write-Host "Gateway:        http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "Auth Service:   http://localhost:8001/docs" -ForegroundColor Yellow
Write-Host "Route Analysis: http://localhost:8004/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "Open frontend/Login.html in your browser or with VS Code Live Server." -ForegroundColor Cyan
