# TrafficVision AI - Multi-Service Local Launcher (Milestone 2)
Write-Host "Starting TrafficVision AI Services..." -ForegroundColor Cyan

# 1. Start Auth Service on port 8001
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting Auth Service on :8001...' -ForegroundColor Green; python -m uvicorn app.main:app --app-dir services/auth --port 8001 --reload"

# 2. Start Traffic Monitoring Service on port 8002
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting Traffic Monitoring Service on :8002...' -ForegroundColor Green; python -m uvicorn app.main:app --app-dir services/traffic-monitoring --port 8002 --reload"

# 3. Start AI Prediction Engine on port 8003
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting AI Prediction Service on :8003...' -ForegroundColor Green; python -m uvicorn app.main:app --app-dir services/ai-engine --port 8003 --reload"

# 4. Start Route Analysis Service on port 8004
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting Route Analysis Service on :8004...' -ForegroundColor Green; python -m uvicorn app.main:app --app-dir services/route-analysis --port 8004 --reload"

# 5. Start Alert Service on port 8005
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting Alert Service on :8005...' -ForegroundColor Green; python -m uvicorn app.main:app --app-dir services/alerts --port 8005 --reload"

# 6. Start Analytics Service on port 8006
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting Analytics Service on :8006...' -ForegroundColor Green; python -m uvicorn app.main:app --app-dir services/analytics --port 8006 --reload"

Start-Sleep -Seconds 2

# 7. Start API Gateway on port 8000
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting API Gateway on :8000...' -ForegroundColor Green; $env:AUTH_SERVICE_URL='http://127.0.0.1:8001'; $env:TRAFFIC_SERVICE_URL='http://127.0.0.1:8002'; $env:PREDICTION_SERVICE_URL='http://127.0.0.1:8003'; $env:ROUTE_ANALYSIS_SERVICE_URL='http://127.0.0.1:8004'; $env:ALERT_SERVICE_URL='http://127.0.0.1:8005'; $env:ANALYTICS_SERVICE_URL='http://127.0.0.1:8006'; python -m uvicorn app.main:app --app-dir services/gateway --port 8000 --reload"

Write-Host ""
Write-Host "All 7 TrafficVision AI services launched!" -ForegroundColor Green
Write-Host "  API Gateway:         http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "  Auth Service:        http://localhost:8001/docs" -ForegroundColor Yellow
Write-Host "  Traffic Monitoring:  http://localhost:8002/docs" -ForegroundColor Yellow
Write-Host "  AI Engine:           http://localhost:8003/docs" -ForegroundColor Yellow
Write-Host "  Route Analysis:      http://localhost:8004/docs" -ForegroundColor Yellow
Write-Host "  Alert Service:       http://localhost:8005/docs" -ForegroundColor Yellow
Write-Host "  Analytics Service:   http://localhost:8006/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "Open frontend/Login.html in your browser or with VS Code Live Server." -ForegroundColor Cyan
