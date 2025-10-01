# Reddit Backfill Guide

This guide explains how to use the new Reddit backfill functionality to reprocess existing Reddit articles with the improved URL extraction logic.

## Overview

The Reddit backfill system consists of:

1. **Enhanced RSS Parser** - Automatically detects Reddit feeds and extracts correct article URLs from content field
2. **Database Methods** - Query and update Reddit articles
3. **Celery Tasks** - Process articles in batches for backfill
4. **API Endpoints** - Trigger and monitor backfill operations

## What Changed

Previously, Reddit articles were stored with Reddit comment URLs like:
```
https://www.reddit.com/r/worldnews/comments/1nva7yb/taiwan_will_not_agree_to_5050_chip_production/
```

Now, the system extracts the actual article URLs from Reddit's content field:
```
https://www.reuters.com/world/asia-pacific/taiwan-will-not-agree-50-50-chip-production-deal-with-us-negotiator-says-2025-10-01/
```

## New Components

### 1. Database Methods (`news-scanner/database/articles.py`)

- `get_reddit_articles(limit, skip)` - Query Reddit articles with pagination
- `count_reddit_articles()` - Count total Reddit articles
- `update_article_url(old_url, new_url)` - Update article URLs

### 2. Celery Tasks (`news-scanner/celery_app/tasks.py`)

- `reddit_backfill_task(batch_size, skip)` - Process Reddit articles in batches
- `reddit_backfill_stats_task()` - Get Reddit article statistics

### 3. API Endpoints (`news-scanner/api/routes/summaries.py`)

- `POST /jobs/reddit-backfill` - Trigger Reddit backfill processing
- `GET /jobs/reddit-stats` - Get Reddit article statistics

## Usage Examples

### 1. Get Reddit Statistics

```bash
curl -X GET "http://localhost:8000/jobs/reddit-stats"
```

Response:
```json
{
  "success": true,
  "stats": {
    "total_reddit_articles": 1250,
    "sample_size": 100,
    "reddit_urls_in_sample": 45,
    "external_urls_in_sample": 55,
    "estimated_updates_needed": 45
  },
  "message": "Reddit statistics retrieved successfully"
}
```

### 2. Trigger Reddit Backfill

```bash
# Process first batch of 50 articles
curl -X POST "http://localhost:8000/jobs/reddit-backfill" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "batch_size=50&skip=0"
```

Response:
```json
{
  "success": true,
  "message": "Reddit backfill triggered (batch size: 50, skip: 0)",
  "task_id": "abc123-def456-ghi789",
  "job_type": "reddit_backfill",
  "batch_size": 50,
  "skip": 0
}
```

### 3. Process All Reddit Articles

```bash
# First batch
curl -X POST "http://localhost:8000/jobs/reddit-backfill" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "batch_size=100&skip=0"

# Second batch
curl -X POST "http://localhost:8000/jobs/reddit-backfill" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "batch_size=100&skip=100"

# Continue until all articles are processed...
```

### 4. Check Task Status

```bash
curl -X GET "http://localhost:8000/jobs/status/{task_id}"
```

### 5. Python Script Usage

```python
from celery_app.tasks import reddit_backfill_task, reddit_backfill_stats_task

# Get statistics
stats = reddit_backfill_stats_task()
print(f"Total Reddit articles: {stats['total_reddit_articles']}")

# Process articles in batches
result = reddit_backfill_task(batch_size=50, skip=0)
print(f"Processed: {result['articles_processed']}, Updated: {result['articles_updated']}")
```

## Monitoring Progress

### 1. Check Celery Worker Logs

```bash
docker-compose logs -f celery-worker
```

Look for messages like:
```
🔄 Starting Reddit backfill task (batch_size=50, skip=0)
Found 50 Reddit articles to process
Updating Reddit article URL: https://www.reddit.com/... -> https://www.reuters.com/...
✅ Reddit backfill completed: 45/50 articles updated
```

### 2. Monitor Database Changes

```python
from news_scanner.database.articles import article_repository

# Count Reddit articles
count = await article_repository.count_reddit_articles()
print(f"Total Reddit articles: {count}")

# Get sample articles
articles = await article_repository.get_reddit_articles(limit=10)
for article in articles:
    print(f"URL: {article.url}")
```

## Configuration

### Celery Task Routing

The Reddit backfill tasks are configured to run on the `low` priority queue:

```python
task_routes={
    'celery_app.tasks.reddit_backfill_task': {'queue': 'low'},
    'celery_app.tasks.reddit_backfill_stats_task': {'queue': 'low'},
}
```

### Batch Size Recommendations

- **Small batches (10-25)**: For testing or when system resources are limited
- **Medium batches (50-100)**: For normal processing
- **Large batches (200+)**: For bulk processing when system has sufficient resources

## Error Handling

The backfill tasks include comprehensive error handling:

- Individual article processing errors are logged but don't stop the batch
- Database connection issues trigger automatic reconnection
- Task failures are logged with detailed error information

## Performance Considerations

1. **Database Load**: Large batches may impact database performance
2. **Memory Usage**: Processing many articles simultaneously uses more memory
3. **Network**: URL extraction involves regex processing, which is CPU-intensive

## Troubleshooting

### Common Issues

1. **No Reddit articles found**
   - Check if articles exist with `origin` field containing "reddit.com"
   - Verify database connection

2. **URL extraction not working**
   - Check if article content contains the expected HTML structure
   - Verify the RSS parser is correctly detecting Reddit feeds

3. **Task not starting**
   - Check Celery worker is running
   - Verify Redis connection
   - Check task queue configuration

### Debug Commands

```bash
# Check Celery worker status
docker-compose exec celery-worker celery -A celery_app.celery_worker status

# Check Redis connection
docker-compose exec redis redis-cli ping

# Check database connection
docker-compose exec mongodb mongo --eval "db.runCommand('ping')"
```

## Future Enhancements

Potential improvements for the Reddit backfill system:

1. **Progress Tracking**: Add progress bars for long-running backfill operations
2. **Resume Capability**: Allow resuming interrupted backfill operations
3. **Selective Processing**: Process only articles that need URL updates
4. **Batch Optimization**: Automatically determine optimal batch sizes
5. **Real-time Monitoring**: Web dashboard for backfill progress

## Conclusion

The Reddit backfill functionality provides a robust way to reprocess existing Reddit articles with the improved URL extraction logic. The system is designed to be:

- **Scalable**: Process articles in configurable batches
- **Reliable**: Comprehensive error handling and logging
- **Monitorable**: API endpoints and detailed logging for progress tracking
- **Flexible**: Configurable batch sizes and pagination support

Use this system to ensure all your Reddit articles have the correct external URLs for better content analysis and readability scoring.
