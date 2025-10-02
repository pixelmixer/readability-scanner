@echo off
REM SigNoz Startup Script for News Analysis System
REM This script starts the SigNoz observability platform and the news analysis services

echo 🚀 Starting SigNoz Observability Platform for News Analysis System
echo ==================================================================

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not running. Please start Docker first.
    pause
    exit /b 1
)

REM Create necessary directories
echo 📁 Creating SigNoz directories...
if not exist "signoz\data\clickhouse" mkdir "signoz\data\clickhouse"
if not exist "signoz\logs" mkdir "signoz\logs"

REM Start SigNoz services first
echo 🔧 Starting SigNoz services...
docker-compose up -d signoz-clickhouse signoz-otel-collector signoz-query-service signoz-frontend signoz-alertmanager

REM Wait for SigNoz to be ready
echo ⏳ Waiting for SigNoz to initialize (this may take a few minutes)...
timeout /t 30 /nobreak >nul

REM Check if SigNoz is ready
echo 🔍 Checking SigNoz status...
curl -s http://localhost:3301 >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ SigNoz frontend is ready!
) else (
    echo ⚠️  SigNoz frontend is not ready yet, but continuing...
)

REM Rebuild and start the news analysis services
echo 🔨 Rebuilding services with OpenTelemetry support...
docker-compose build hug
docker-compose up -d

echo.
echo 🎉 Setup Complete!
echo ==================
echo.
echo 📊 SigNoz Dashboard: http://localhost:3301
echo 🔍 Query Service: http://localhost:8080
echo 📈 News Scanner: http://localhost:4913
echo 🤗 Hug API: http://localhost:3839
echo 🌉 RSS Bridge: http://localhost:3939
echo 🌸 Celery Flower: http://localhost:5555
echo.
echo 📋 To view logs:
echo    docker-compose logs -f [service-name]
echo.
echo 🛑 To stop all services:
echo    docker-compose down
echo.
echo 📚 For more information, check the SigNoz documentation:
echo    https://signoz.io/docs/
pause
