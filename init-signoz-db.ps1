# SigNoz Database Initialization Script
# This script initializes the required ClickHouse database and tables for SigNoz

Write-Host "Initializing SigNoz Database Schema" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green

# Check if ClickHouse is running
Write-Host "Checking if ClickHouse is running..." -ForegroundColor Yellow
try {
    docker exec crawltest-signoz-clickhouse-1 clickhouse-client --query "SELECT 1" | Out-Null
    Write-Host "ClickHouse is running" -ForegroundColor Green
} catch {
    Write-Host "ClickHouse is not running. Please start it first with:" -ForegroundColor Red
    Write-Host "   docker-compose up -d signoz-clickhouse" -ForegroundColor White
    exit 1
}

# Create database
Write-Host "Creating signoz_metrics database..." -ForegroundColor Yellow
try {
    docker exec crawltest-signoz-clickhouse-1 clickhouse-client --query "CREATE DATABASE IF NOT EXISTS signoz_metrics"
    Write-Host "Database created/verified" -ForegroundColor Green
} catch {
    Write-Host "Failed to create database" -ForegroundColor Red
    exit 1
}

# Create table
Write-Host "Creating distributed_updated_metadata table..." -ForegroundColor Yellow
try {
    docker exec crawltest-signoz-clickhouse-1 clickhouse-client --query "CREATE TABLE IF NOT EXISTS signoz_metrics.distributed_updated_metadata (metric_name String, type String, description String, temporality String, is_monotonic UInt8, unit String, updated_at DateTime DEFAULT now()) ENGINE = MergeTree() ORDER BY metric_name"
    Write-Host "Table created/verified" -ForegroundColor Green
} catch {
    Write-Host "Failed to create table" -ForegroundColor Red
    exit 1
}

# Verify the setup
Write-Host "Verifying database setup..." -ForegroundColor Yellow
try {
    $result = docker exec crawltest-signoz-clickhouse-1 clickhouse-client --query "SHOW TABLES FROM signoz_metrics"
    if ($result -match "distributed_updated_metadata") {
        Write-Host "Database setup verified successfully!" -ForegroundColor Green
    } else {
        Write-Host "Table not found in verification" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Could not verify setup, but database operations completed" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Database initialization complete!" -ForegroundColor Green
Write-Host "You can now start the SigNoz Query Service:" -ForegroundColor Cyan
Write-Host "   docker-compose up -d signoz-query-service" -ForegroundColor White