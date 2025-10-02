# SigNoz Startup Script for News Analysis System (PowerShell)
# This script starts the SigNoz observability platform and the news analysis services

Write-Host "Starting SigNoz Observability Platform for News Analysis System" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green

# Check if Docker is running
try {
    docker info | Out-Null
    Write-Host "Docker is running" -ForegroundColor Green
}
catch {
    Write-Host "Docker is not running. Please start Docker first." -ForegroundColor Red
    exit 1
}

# Create necessary directories
Write-Host "Creating SigNoz directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "signoz\data\clickhouse" | Out-Null
New-Item -ItemType Directory -Force -Path "signoz\logs" | Out-Null

# Start ClickHouse first
Write-Host "Starting ClickHouse..." -ForegroundColor Yellow
docker-compose up -d signoz-clickhouse

# Wait for ClickHouse to be ready
Write-Host "Waiting for ClickHouse to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Initialize SigNoz database and tables
Write-Host "Initializing SigNoz database schema..." -ForegroundColor Yellow
try {
    docker exec crawltest-signoz-clickhouse-1 clickhouse-client --query "CREATE DATABASE IF NOT EXISTS signoz_metrics"
    Write-Host "Database created/verified" -ForegroundColor Green
}
catch {
    Write-Host "Database may already exist" -ForegroundColor Yellow
}

try {
    docker exec crawltest-signoz-clickhouse-1 clickhouse-client --query "CREATE TABLE IF NOT EXISTS signoz_metrics.distributed_updated_metadata (metric_name String, type String, description String, temporality String, is_monotonic UInt8, unit String, updated_at DateTime DEFAULT now()) ENGINE = MergeTree() ORDER BY metric_name"
    Write-Host "Table created/verified" -ForegroundColor Green
}
catch {
    Write-Host "Table may already exist" -ForegroundColor Yellow
}

# Start remaining SigNoz services
Write-Host "Starting remaining SigNoz services..." -ForegroundColor Yellow
docker-compose up -d signoz-otel-collector signoz-query-service signoz-frontend

# Wait for SigNoz to be ready
Write-Host "Waiting for SigNoz services to initialize (this may take a few minutes)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Check if SigNoz is ready
Write-Host "Checking SigNoz status..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3301" -TimeoutSec 10 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "SigNoz frontend is ready!" -ForegroundColor Green
    }
}
catch {
    Write-Host "SigNoz frontend is not ready yet, but continuing..." -ForegroundColor Yellow
}

# Start the news analysis services
Write-Host "Starting news analysis services..." -ForegroundColor Yellow
docker-compose up -d

Write-Host ""
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "===============" -ForegroundColor Green
Write-Host ""
Write-Host "SigNoz Dashboard: http://localhost:3301" -ForegroundColor Cyan
Write-Host "Query Service: http://localhost:8080" -ForegroundColor Cyan
Write-Host "News Scanner: http://localhost:4913" -ForegroundColor Cyan
Write-Host "Hug API: http://localhost:3839" -ForegroundColor Cyan
Write-Host "RSS Bridge: http://localhost:3939" -ForegroundColor Cyan
Write-Host "Celery Flower: http://localhost:5555" -ForegroundColor Cyan
Write-Host ""
Write-Host "To view logs:" -ForegroundColor Yellow
Write-Host "   docker-compose logs -f [service-name]" -ForegroundColor White
Write-Host ""
Write-Host "To stop all services:" -ForegroundColor Yellow
Write-Host "   docker-compose down" -ForegroundColor White
Write-Host ""
Write-Host "For more information, check the SigNoz documentation:" -ForegroundColor Yellow
Write-Host "   https://signoz.io/docs/" -ForegroundColor White