# SigNoz Setup Documentation

This document explains how to set up and manage the SigNoz observability platform for the news analysis system.

## Quick Start

### Simple Docker Compose (Recommended)
```bash
# Start everything with automatic database initialization
docker-compose up -d

# Or use the simple startup script
.\start-signoz-simple.ps1  # Windows
./start-signoz-simple.sh   # Linux/macOS
```

### Manual Steps
```bash
# 1. Start ClickHouse
docker-compose up -d signoz-clickhouse

# 2. Wait for ClickHouse to be ready
sleep 15

# 3. Initialize database
docker-compose up signoz-db-init

# 4. Start remaining services
docker-compose up -d
```

## How It Works

### Docker-Native Database Initialization
The system now uses a dedicated `signoz-db-init` container that:
1. Waits for ClickHouse to be ready
2. Creates the `signoz_metrics` database
3. Creates the `distributed_updated_metadata` table with the correct schema
4. Verifies the setup
5. Exits (one-time initialization)

### Service Dependencies
The correct startup order is handled automatically:
1. `signoz-clickhouse` - Database server
2. `signoz-db-init` - Database initialization (runs once)
3. `signoz-query-service` - API backend
4. `signoz-frontend` - Web dashboard
5. `signoz-otel-collector` - Metrics collection
6. All other services

### Legacy Scripts (Optional)
The PowerShell/bash scripts are still available for manual control:
- `init-signoz-db.ps1` / `init-signoz-db.sh` - Manual database initialization
- `start-signoz.ps1` / `start-signoz.sh` - Full manual startup

## Manual Database Setup

If you need to set up the database manually:

```bash
# Start ClickHouse
docker-compose up -d signoz-clickhouse

# Wait for it to be ready
sleep 15

# Create database
docker exec crawltest-signoz-clickhouse-1 clickhouse-client --query "CREATE DATABASE IF NOT EXISTS signoz_metrics"

# Create table
docker exec crawltest-signoz-clickhouse-1 clickhouse-client --query "CREATE TABLE IF NOT EXISTS signoz_metrics.distributed_updated_metadata (metric_name String, type String, description String, temporality String, is_monotonic UInt8, unit String, updated_at DateTime DEFAULT now()) ENGINE = MergeTree() ORDER BY metric_name"
```

## Service URLs

- **SigNoz Dashboard**: http://localhost:3301
- **Query Service API**: http://localhost:8080
- **ClickHouse**: localhost:9000
- **OTEL Collector**: localhost:4317 (gRPC), localhost:4318 (HTTP), localhost:8889 (Prometheus)

## Troubleshooting

### Query Service Errors
If you see errors like "Database signoz_metrics does not exist" or "Table distributed_updated_metadata does not exist":
1. Run the database initialization script
2. Restart the query service: `docker-compose restart signoz-query-service`

### Frontend Not Loading
If the frontend returns empty responses:
1. Check the port mapping in docker-compose.yml (should be `3301:3301`)
2. Restart the frontend: `docker-compose restart signoz-frontend`

### Service Dependencies
The correct startup order is:
1. ClickHouse
2. Database initialization
3. Query Service
4. Frontend
5. OTEL Collector

## Clean Restart

To start completely fresh:
```bash
# Stop everything
docker-compose down

# Remove volumes (WARNING: This will delete all data)
docker-compose down -v

# Start fresh
.\start-signoz.ps1  # or ./start-signoz.sh
```

## Monitoring

Check service status:
```bash
docker-compose ps
```

View logs:
```bash
docker-compose logs -f signoz-query-service
docker-compose logs -f signoz-frontend
docker-compose logs -f signoz-clickhouse
```
