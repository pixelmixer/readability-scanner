# Daily Topics Architecture Fix

## Issue

Initially implemented topic grouping with ML dependencies (sklearn) in the news-scanner container, violating the architecture principle: **"No ML dependencies (ML operations handled by ml-service)"**

## Resolution

Properly separated concerns following the microservice architecture:

### ML Service (ml-service/)
**Responsibilities:**
- All ML calculations (embeddings, similarity, clustering)
- Topic grouping logic with scikit-learn
- Direct database access for article fetching

**New Endpoint:**
```http
POST /topics/generate-daily-topics
Content-Type: application/json

{
  "days_back": 7,
  "similarity_threshold": 0.65,
  "min_group_size": 2
}
```

**Response:**
```json
{
  "success": true,
  "topic_groups": [...],
  "articles_processed": 3712,
  "articles_grouped": 450
}
```

### News Scanner (news-scanner/)
**Responsibilities:**
- Call ML service API for grouping
- Generate combined summaries (using LLM)
- Store final topic groups in `daily_topics` collection
- NO ML dependencies

**Flow:**
1. Celery task triggered (hourly or manual)
2. Call `ml_client.generate_daily_topics()` → ML service
3. ML service returns topic groups
4. Generate combined summary for each group
5. Store in MongoDB

## Files Modified

### Added in ml-service/
```python
# ml-service/main.py
@app.post("/topics/generate-daily-topics")
async def generate_daily_topics(request: DailyTopicsRequest):
    # Fetches articles, calculates similarities, creates groups
    # Uses numpy and sklearn (already installed in ml-service)
```

### Modified in news-scanner/
```python
# news-scanner/services/ml_client.py
async def generate_daily_topics(...) -> Dict[str, Any]:
    # Calls ML service API, no local calculations

# news-scanner/celery_app/jobs/daily_topics_jobs.py
async def generate_daily_topics() -> Dict[str, Any]:
    # 1. Call ml_client.generate_daily_topics()
    # 2. Generate combined summaries
    # 3. Store in daily_topics collection
```

### Reverted
```python
# news-scanner/requirements.txt
# REMOVED: scikit-learn==1.3.2
```

## Architecture Principles Followed

1. **Separation of Concerns**
   - ML operations → ML service
   - Business logic → News scanner
   - Task scheduling → Celery workers

2. **Microservice Communication**
   - HTTP API calls between services
   - Asynchronous where possible
   - Proper error handling and timeouts

3. **Dependency Management**
   - Heavy ML libraries only in ml-service
   - News scanner stays lightweight
   - Clear dependency boundaries

## Testing

### 1. Rebuild ML Service
```bash
docker-compose build ml-service
docker-compose restart ml-service
```

### 2. Restart News Scanner & Celery
```bash
docker-compose restart news-scanner celery-worker
```

### 3. Test ML Service Endpoint Directly
```bash
curl -X POST http://localhost:30003/topics/generate-daily-topics \
  -H "Content-Type: application/json" \
  -d '{
    "days_back": 7,
    "similarity_threshold": 0.65,
    "min_group_size": 2
  }' | jq
```

### 4. Trigger Celery Task
```bash
docker-compose exec celery-worker celery -A celery_app.celery_worker call celery_app.tasks.generate_daily_topics_task
```

### 5. Check Results
```bash
# Check MongoDB
docker-compose exec mongodb mongosh news_analysis
> db.daily_topics.countDocuments()
> db.daily_topics.find().pretty()

# Check logs
docker-compose logs -f ml-service | grep "daily topics"
docker-compose logs -f celery-worker | grep "daily topics"
```

## Benefits of This Architecture

1. **Scalability**
   - ML service can be scaled independently
   - Can run on GPU-enabled instances
   - News scanner remains lightweight

2. **Maintainability**
   - Clear separation of ML and business logic
   - Easier to upgrade ML libraries
   - Fewer dependency conflicts

3. **Performance**
   - ML service optimized for computation
   - Can implement caching at ML layer
   - Better resource utilization

4. **Testing**
   - ML operations testable independently
   - Can mock ML service for integration tests
   - Clearer test boundaries

## Related Documentation

- [Main Implementation Guide](TODAY_TOPICS_IMPLEMENTATION.md)
- [ML Service Documentation](../ml-service/README.md)
- [Celery Queue System](CELERY_QUEUE_SYSTEM.md)

