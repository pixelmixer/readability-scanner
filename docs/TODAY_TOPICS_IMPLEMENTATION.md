# Today's Topics Implementation

## Overview

This document describes the implementation of the "Today's Topics" feature - a new home page that displays topic-grouped articles with combined summaries, updated hourly by Celery workers.

## Implementation Date

October 13, 2024

## Components Implemented

### 1. Summary Service Extension

**File:** `news-scanner/services/summary_service.py`

Added `generate_combined_summary()` method that:
- Takes multiple article summaries as input
- Generates a comprehensive overview using the LLM API
- Returns combined summary with metadata

### 2. Celery Jobs

**File:** `news-scanner/celery_app/jobs/daily_topics_jobs.py`

New tasks:
- `generate_daily_topics_sync()` - Main task that:
  - Fetches articles from last 7 days with summaries and embeddings
  - Groups similar articles using cosine similarity (threshold: 0.75)
  - Generates combined summaries for each topic group
  - Stores results in `daily_topics` collection
  
- `regenerate_daily_topics_sync()` - Manual trigger for regeneration

Both use proper async/sync wrappers for Celery compatibility.

### 3. Celery Configuration

**File:** `news-scanner/celery_app/celery_worker.py`

Added:
- Task routing for daily topics tasks
- Hourly beat schedule: `hourly-daily-topics-update` runs at minute 0 of every hour
- Queue assignments:
  - `generate_daily_topics_task` → `low` queue (priority 2)
  - `regenerate_daily_topics_task` → `high` queue (priority 10)

### 4. Task Registration

**File:** `news-scanner/celery_app/tasks.py`

Registered:
- `generate_daily_topics_task` - Scheduled hourly task
- `regenerate_daily_topics_task` - User-triggered manual regeneration

### 5. API Routes

**File:** `news-scanner/api/routes/daily_topics_routes.py`

Endpoints:
- `GET /api/daily-topics/today` - Fetch current topic groups
- `POST /api/daily-topics/regenerate` - Trigger manual regeneration
- `GET /api/daily-topics/stats` - Get statistics about topics

### 6. Application Integration

**File:** `news-scanner/api/app.py`

Changes:
- Imported and registered `daily_topics_routes`
- Changed root route `/` to serve `today_topics.html` instead of redirecting to sources
- Today's Topics is now the home page

### 7. Frontend Template

**File:** `news-scanner/templates/pages/today_topics.html`

Features:
- Modern card-based layout for topic groups
- Each topic card shows:
  - Combined summary at the top
  - Article count badge
  - Expandable list of articles with individual summaries
  - Publication dates and sources
- Manual regeneration button
- Loading and error states
- Responsive design

### 8. Navigation Update

**File:** `news-scanner/templates/layouts/base.html`

Changes:
- Added "Today's Topics" as first navigation item (home icon)
- Links to `/` 
- Kept existing "Today's News" link to `/newspaper`

## Database Schema

### Collection: `daily_topics`

```json
{
  "topic_id": "20241013_1",
  "date_generated": "2024-10-13T10:00:00Z",
  "article_count": 5,
  "articles": [
    {
      "url": "https://...",
      "title": "Article Title",
      "summary": "Article summary...",
      "publication_date": "2024-10-13T09:30:00Z",
      "origin": "Reuters",
      "host": "reuters.com",
      "image_url": "https://...",
      "author": "John Doe"
    }
  ],
  "combined_summary": "Overview of all articles in this topic...",
  "combined_summary_status": "completed",
  "combined_summary_error": null,
  "created_at": "2024-10-13T10:00:00Z",
  "date_range_start": "2024-10-06T00:00:00Z",
  "date_range_end": "2024-10-13T23:59:59Z"
}
```

## How It Works

### Automatic Updates (Hourly)

1. **Celery Beat** triggers `generate_daily_topics_task` every hour
2. Task fetches articles from last 7 days with:
   - Valid publication_date
   - Completed summaries
   - Embeddings generated
3. Groups articles by similarity (threshold: 0.75, min 2 articles per group)
4. Generates combined summary for each group
5. Clears old topics and inserts new ones in `daily_topics` collection
6. Users see updated topics on next page load

### Manual Regeneration

1. User clicks "Regenerate Topics" button
2. Frontend posts to `/api/daily-topics/regenerate`
3. Task queued with high priority
4. Modal shows "in progress" message
5. After 5 seconds, page reloads to show updated topics

### Page Load

1. User visits `/` (home page)
2. JavaScript loads `/api/daily-topics/today`
3. API fetches from `daily_topics` collection
4. Frontend renders topic cards with:
   - Combined summaries
   - Expandable article lists
   - Metadata (count, dates)

## Concurrency Handling

All tasks follow proper async/sync patterns:

```python
def task_sync(*args):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(task_async(*args))
    finally:
        loop.close()
```

This ensures:
- No conflicts between async and sync code
- Proper event loop management in Celery workers
- Clean resource cleanup

## Queue Assignments

- **High Queue:** Manual regeneration (user-initiated)
- **Normal Queue:** Not used for topics
- **Low Queue:** Hourly scheduled generation

## Testing

To test the implementation:

1. **Check task registration:**
   ```bash
   docker-compose exec celery-worker celery -A celery_app.celery_worker inspect registered
   ```

2. **Manually trigger generation:**
   ```bash
   docker-compose exec celery-worker celery -A celery_app.celery_worker call celery_app.tasks.generate_daily_topics_task
   ```

3. **Check MongoDB:**
   ```javascript
   db.daily_topics.find().pretty()
   ```

4. **Access frontend:**
   - Navigate to `http://localhost:30002/`
   - Should see Today's Topics page
   - Click "Regenerate Topics" to test manual trigger

## Monitoring

### Celery Flower

Monitor task execution:
```
http://localhost:30006
```

### API Stats

Check topic statistics:
```bash
curl http://localhost:30002/api/daily-topics/stats
```

### Logs

View task execution logs:
```bash
docker-compose logs -f celery-worker | grep daily_topics
```

## Future Enhancements

Possible improvements:

1. **Caching:** Add Redis caching for API responses
2. **Filtering:** Allow users to filter topics by source or date
3. **Search:** Add search within topic groups
4. **Notifications:** Email/push notifications for new major topics
5. **Trending:** Highlight topics with most articles or highest engagement
6. **Persistence:** Keep historical topic snapshots for time-based analysis
7. **ML Improvements:** Use more sophisticated clustering algorithms
8. **Performance:** Implement pagination for large numbers of topics

## Dependencies

This feature relies on:

- MongoDB for data storage
- Celery + Redis for task scheduling
- LLM API for combined summary generation
- ML service for embeddings (optional, can use local generation)
- Existing article summaries

## Troubleshooting

### No topics appearing

1. Check if articles have embeddings: `db.documents.countDocuments({embedding: {$exists: true}})`
2. Check if articles have summaries: `db.documents.countDocuments({summary_processing_status: "completed"})`
3. Check Celery worker logs for errors
4. Manually trigger generation to test

### Combined summaries failing

1. Check LLM API connectivity
2. Verify summary_service configuration
3. Check API logs for error messages
4. Ensure articles have individual summaries

### Hourly updates not running

1. Check Celery Beat is running: `docker-compose ps celery-beat`
2. Verify beat schedule in celery_worker.py
3. Check beat logs: `docker-compose logs celery-beat`
4. Manually trigger to verify task works

## Related Documentation

- [Topic Analysis README](TOPIC_ANALYSIS_README.md)
- [Celery Queue System](CELERY_QUEUE_SYSTEM.md)
- [Getting Started](GETTING_STARTED.md)

