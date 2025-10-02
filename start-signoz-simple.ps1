# Simple SigNoz Startup Script
# This script starts SigNoz with automatic database initialization

Write-Host "Starting SigNoz with automatic database initialization..." -ForegroundColor Green

# Start ClickHouse first
Write-Host "Starting ClickHouse..." -ForegroundColor Yellow
docker-compose up -d signoz-clickhouse

# Wait for ClickHouse to be ready
Write-Host "Waiting for ClickHouse to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Run database initialization
Write-Host "Initializing database..." -ForegroundColor Yellow
docker-compose up signoz-db-init

# Start remaining services
Write-Host "Starting remaining services..." -ForegroundColor Yellow
docker-compose up -d

Write-Host ""
Write-Host "SigNoz is ready!" -ForegroundColor Green
Write-Host "Dashboard: http://localhost:3301" -ForegroundColor Cyan
Write-Host "Query Service: http://localhost:8080" -ForegroundColor Cyan
