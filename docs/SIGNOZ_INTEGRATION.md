# SigNoz Integration for News Analysis System

## Overview

This document describes the integration of [SigNoz](https://signoz.io/) observability platform with the news analysis system. SigNoz provides comprehensive monitoring, logging, and tracing capabilities for all services in the system.

## What is SigNoz?

SigNoz is an open-source alternative to Datadog and New Relic that provides:
- **Logs**: Centralized log collection and analysis
- **Metrics**: Application and infrastructure metrics
- **Traces**: Distributed tracing for request flows
- **Dashboards**: Customizable monitoring dashboards
- **Alerts**: Configurable alerting system

## Architecture

```
News Analysis Services → OpenTelemetry → SigNoz Collector → ClickHouse → SigNoz UI
```

### Services Monitored

1. **News Scanner** (FastAPI) - Main application
2. **Hug API** (Python) - ML and analytics API
3. **RSS Bridge** (PHP) - RSS feed generation
4. **MongoDB** - Database
5. **Redis** - Message broker
6. **Celery Workers** - Background task processing
7. **Celery Beat** - Task scheduling
8. **Celery Flower** - Task monitoring

## Setup and Configuration

### 1. SigNoz Services

The following SigNoz services are configured in `docker-compose.yml`:

- **signoz-otel-collector**: Collects telemetry data from all services
- **signoz-clickhouse**: Time-series database for storing metrics, logs, and traces
- **signoz-query-service**: Backend API for SigNoz frontend
- **signoz-frontend**: Web UI for monitoring and analysis
- **signoz-alertmanager**: Handles alerting and notifications

### 2. OpenTelemetry Instrumentation

All Python services are instrumented with OpenTelemetry:

#### News Scanner Service
- FastAPI instrumentation
- Celery instrumentation
- MongoDB instrumentation
- Redis instrumentation
- HTTP requests instrumentation

#### Hug API Service
- HTTP requests instrumentation
- MongoDB instrumentation

### 3. Log Configuration

All services are configured with structured JSON logging:
- Log rotation (10MB max, 3 files)
- Service labels for easy filtering
- Centralized log collection via OTLP

## Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **SigNoz Dashboard** | http://localhost:3301 | Main monitoring interface |
| **Query Service** | http://localhost:8080 | Backend API |
| **News Scanner** | http://localhost:4913 | Main application |
| **Hug API** | http://localhost:3839 | ML/Analytics API |
| **RSS Bridge** | http://localhost:3939 | RSS feed generator |
| **Celery Flower** | http://localhost:5555 | Task monitoring |

## Usage

### Starting the System

1. **Windows**: Run `start-signoz.bat`
2. **Linux/Mac**: Run `./start-signoz.sh`
3. **Manual**: `docker-compose up -d`

### Viewing Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f news-scanner
docker-compose logs -f hug
docker-compose logs -f signoz-otel-collector
```

### SigNoz Dashboard Features

1. **Logs Tab**: Search and filter logs from all services
2. **Metrics Tab**: View application and system metrics
3. **Traces Tab**: Track request flows across services
4. **Dashboards Tab**: Create custom monitoring dashboards
5. **Alerts Tab**: Configure and manage alerts

## Configuration Files

### SigNoz Configuration

- `signoz/otel-collector-config.yaml` - OTLP collector configuration
- `signoz/clickhouse-config.xml` - ClickHouse database configuration
- `signoz/query-service-config.yaml` - Query service configuration
- `signoz/alertmanager-config.yaml` - Alert manager configuration

### Service Instrumentation

- `news-scanner/main.py` - OpenTelemetry setup for news scanner
- `news-scanner/api/app.py` - FastAPI instrumentation
- `hug/hug.py` - OpenTelemetry setup for Hug API

## Monitoring Capabilities

### 1. Application Performance Monitoring (APM)
- Request latency and throughput
- Error rates and exceptions
- Database query performance
- External API call monitoring

### 2. Infrastructure Monitoring
- Container resource usage
- Service health checks
- Network connectivity
- Storage utilization

### 3. Business Metrics
- Articles processed per minute
- Readability analysis completion rates
- RSS feed update frequencies
- Task queue processing times

### 4. Log Analysis
- Centralized log aggregation
- Structured log parsing
- Error pattern detection
- Performance bottleneck identification

## Troubleshooting

### Common Issues

1. **Services not appearing in SigNoz**:
   - Check if OpenTelemetry collector is running
   - Verify OTLP endpoint configuration
   - Check service logs for instrumentation errors

2. **High memory usage**:
   - Adjust ClickHouse memory settings
   - Configure log retention policies
   - Monitor collector buffer sizes

3. **Missing traces**:
   - Ensure services are properly instrumented
   - Check OTLP exporter configuration
   - Verify network connectivity between services

### Useful Commands

```bash
# Check service health
docker-compose ps

# View SigNoz collector logs
docker-compose logs -f signoz-otel-collector

# Restart SigNoz services
docker-compose restart signoz-otel-collector signoz-query-service

# Check ClickHouse status
docker-compose logs -f signoz-clickhouse
```

## Data Retention

- **Logs**: 7 days (configurable)
- **Metrics**: 30 days (configurable)
- **Traces**: 7 days (configurable)

## Security Considerations

- SigNoz UI is accessible on localhost only
- No authentication configured (suitable for development)
- For production, configure proper authentication and network security

## Next Steps

1. **Custom Dashboards**: Create dashboards specific to news analysis metrics
2. **Alerting Rules**: Set up alerts for system health and performance
3. **Log Parsing**: Configure custom log parsers for specific error patterns
4. **Performance Optimization**: Use metrics to identify and fix bottlenecks
5. **Production Setup**: Configure authentication and security for production deployment

## Resources

- [SigNoz Documentation](https://signoz.io/docs/)
- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/instrumentation/python/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
