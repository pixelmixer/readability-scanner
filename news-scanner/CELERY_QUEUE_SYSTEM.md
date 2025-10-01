# Celery Queue System Implementation

## Overview

This document describes the new Celery-based queueing system implemented to optimize RSS feed processing and eliminate the bottleneck of simultaneous batch operations.

## Architecture

### Queue Structure

The system uses **Redis** as the message broker with three priority queues:

- 🔴 **High Priority Queue** (`high`): Manual refresh requests from UI
- 🟡 **Normal Priority Queue** (`normal`): Scheduled RSS source scans  
- 🟢 **Low Priority Queue** (`low`): Background maintenance tasks

### Task Types

| Task | Queue | Purpose | Retry Policy |
|------|-------|---------|--------------|
| `manual_refresh_source_task` | `high` | Manual UI refresh requests | 2 retries, 30s intervals |
| `scan_single_source_task` | `normal` | Individual RSS source scans | 3 retries, exponential backoff |
| `scheduled_scan_trigger_task` | `low` | Distributes scheduled scans over time | No retries |

### Worker Configuration

- **Worker Pool**: Single worker with multiple queues
- **Concurrency**: Controlled per-task (no more than 1 concurrent scan per source)
- **Task Acknowledgment**: Late acknowledgment (after completion)
- **Memory Management**: Worker restarts after 50 tasks

## Key Features

### 1. **Eliminates Batch Processing Bottleneck**
- Old system: All RSS feeds processed simultaneously
- New system: Sources are queued and processed individually with staggered timing

### 2. **Prioritized Processing**
- Manual refresh requests get immediate attention (high priority)
- Scheduled scans run at normal priority
- Maintenance tasks run when system is idle (low priority)

### 3. **Smart Scheduling**
- Replaces cron-based batch processing
- Distributes scheduled scans: 0s, 30s, 60s, 90s delays
- Prevents system overload during scheduled runs

### 4. **Enhanced Error Handling**
- Task-specific retry policies
- Exponential backoff for failed tasks
- Detailed logging and error tracking

## API Endpoints

### Queue Management

```http
GET /sources/queue/status
```
Get current queue statistics and worker status.

```http
GET /sources/queue/task/{task_id}
```
Check status of a specific task.

```http
POST /sources/queue/trigger-scan
```
Manually trigger scheduled scan for all sources.

```http
DELETE /sources/queue/task/{task_id}
```
Cancel a pending or running task.

### Updated Source Management

```http
POST /sources/refresh/{source_id}?wait_for_result=true
```
- `wait_for_result=true` (default): Wait for task completion, return results
- `wait_for_result=false`: Queue task immediately, return task ID

## Usage Patterns

### Manual Refresh (Synchronous)
```python
# Frontend makes request
POST /sources/refresh/12345

# System queues high-priority task
# Waits up to 5 minutes for completion
# Returns scan results to frontend
```

### Scheduled Processing (Asynchronous)  
```python
# Celery beat triggers every 1 hour
scheduled_scan_trigger_task()

# Task gets all source URLs
# Queues individual scan tasks with staggered timing
# Returns immediately, processing continues in background
```

### Background Operations
- New source addition → immediate normal-priority scan
- Source URL change → immediate normal-priority scan  
- Weekly cleanup → low-priority maintenance task

## Monitoring

### Celery Flower Dashboard
Access at: `http://localhost:5555`
- Real-time task monitoring
- Worker status and statistics
- Queue lengths and processing rates

### Queue Status API
```json
{
  "success": true,
  "timestamp": "2024-01-15T10:30:00Z",
  "total_active_tasks": 3,
  "queues": {
    "high": {"active": 1, "description": "Manual refresh requests"},
    "normal": {"active": 2, "description": "Scheduled source scans"}, 
    "low": {"active": 0, "description": "Maintenance tasks"}
  },
  "workers": {
    "celery@worker1": {
      "active_tasks": 3,
      "task_details": [...]
    }
  }
}
```

## Migration from Old System

### What Changed
1. **Cron scheduling** → **Celery beat scheduling**
2. **Batch processing** → **Individual queued tasks**  
3. **Synchronous operations** → **Asynchronous with priority**
4. **No retry logic** → **Smart retry policies**

### What Stayed the Same
- Same MongoDB collections and schema
- Same RSS parsing and readability analysis logic
- Same API response formats
- Same Docker service architecture

## Performance Benefits

1. **Reduced System Load**: No more simultaneous processing of all sources
2. **Better Resource Utilization**: Tasks are distributed over time
3. **Improved UI Responsiveness**: Manual refreshes get priority processing
4. **Failure Isolation**: One failed source doesn't impact others
5. **Horizontal Scalability**: Easy to add more workers as needed

## Configuration

Key environment variables in `.env`:

```bash
# Celery Configuration  
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Scanning Configuration
SCAN_INTERVAL=0 * * * *  # Every 1 hour
MAX_CONCURRENT_SCANS=5     # Concurrent scan limit
```

## Deployment

1. **Start the services**:
   ```bash
   docker-compose up -d
   ```

2. **Verify Celery is running**:
   ```bash
   docker-compose logs celery-worker
   docker-compose logs celery-beat
   ```

3. **Access monitoring**:
   - Flower dashboard: http://localhost:5555
   - Queue status API: http://localhost:4913/sources/queue/status

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   - Check `docker-compose logs redis`
   - Verify Redis service is running

2. **Tasks Not Processing**
   - Check `docker-compose logs celery-worker`
   - Verify worker is connected to Redis

3. **Scheduled Scans Not Running**
   - Check `docker-compose logs celery-beat`
   - Verify beat scheduler is running

### Debugging Commands

```bash
# Check all services
docker-compose ps

# View Celery worker logs
docker-compose logs -f celery-worker

# Check Redis connectivity
docker-compose exec redis redis-cli ping

# View queue statistics
curl http://localhost:4913/sources/queue/status
```

