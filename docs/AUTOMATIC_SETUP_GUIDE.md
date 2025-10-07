# Automatic Topic Analysis Setup Guide

This guide explains how the topic analysis system automatically initializes and maintains itself without manual intervention.

## 🚀 Automatic Startup Process

When the container starts up, the system automatically:

1. **Initializes Vector Service**: Loads the embedding model (`all-MiniLM-L6-v2`)
2. **Checks Article Status**: Counts total articles vs. articles with embeddings
3. **Queues Missing Embeddings**: Automatically generates embeddings for articles that don't have them
4. **Starts Maintenance Schedulers**: Begins scheduled maintenance tasks

## 📅 Scheduled Maintenance

The system runs several automated maintenance tasks:

### Every 2 Hours
- **Embedding Generation**: Processes any new articles that don't have embeddings
- **Batch Size**: 100 articles per batch to manage memory usage

### Daily at 2:00 AM
- **Topic Grouping**: Groups articles by similarity (threshold: 0.75, min group size: 2)
- **Processes**: All articles with embeddings

### Daily at 3:00 AM
- **Summary Generation**: Creates shared summaries for all topic groups
- **Runs After**: Topic grouping to ensure groups exist

### Weekly (Sunday at 4:00 AM)
- **Cleanup**: Removes topic groups older than 30 days
- **Prevents**: Database bloat from accumulating old data

## 🔧 Management Interface

Access the management interface at: `http://localhost:30005/topic-management`

### Features:
- **Real-time Statistics**: View system status and coverage
- **Manual Triggers**: Start tasks manually if needed
- **Scheduler Status**: Monitor scheduled job status
- **Task Results**: View results of recent operations

## 📊 Monitoring

### Health Check
The system status is included in the main health check:
```http
GET /health
```

Response includes:
```json
{
  "topic_scheduler": {
    "running": true,
    "jobs": [
      {
        "id": "topic_embedding_generation",
        "name": "Generate Missing Embeddings",
        "next_run": "2024-01-01T14:00:00Z"
      }
    ]
  }
}
```

### API Endpoints
- **Statistics**: `GET /api/topic-management/stats`
- **Scheduler Status**: `GET /api/topic-management/scheduler-status`
- **Manual Triggers**: `POST /api/topic-management/{action}`

## 🔄 Automatic Processing Flow

### New Article Processing
1. **Article Scanned**: RSS scanner processes new article
2. **Readability Analysis**: Standard readability metrics calculated
3. **Database Storage**: Article saved to MongoDB
4. **Embedding Queue**: If article is new, embedding generation queued automatically
5. **Background Processing**: Celery worker generates embedding
6. **Vector Storage**: Embedding stored in article document

### Topic Group Updates
1. **Scheduled Grouping**: Daily topic grouping runs
2. **Similarity Analysis**: Articles grouped by vector similarity
3. **Group Storage**: Topic groups saved to `article_topics` collection
4. **Summary Generation**: Shared summaries created for each group

## ⚙️ Configuration

### Environment Variables
No additional configuration needed - the system uses existing settings.

### Customization
To modify schedules, edit `news-scanner/scheduler/topic_scheduler.py`:

```python
# Change embedding generation frequency
CronTrigger(hour="*/1", minute=0)  # Every hour instead of 2 hours

# Change topic grouping schedule
CronTrigger(hour=1, minute=0)  # 1 AM instead of 2 AM

# Change cleanup frequency
CronTrigger(day_of_week=0, hour=5, minute=0)  # Sunday at 5 AM
```

## 🚨 Troubleshooting

### Check System Status
```bash
# View container logs
docker-compose logs -f news-scanner

# Check health endpoint
curl http://localhost:30005/health

# View management interface
open http://localhost:30005/topic-management
```

### Common Issues

1. **No Embeddings Generated**
   - Check if Celery worker is running
   - Verify database connection
   - Check logs for errors

2. **Scheduler Not Running**
   - Restart the news-scanner container
   - Check for startup errors in logs

3. **Memory Issues**
   - Reduce batch size in scheduler
   - Monitor container memory usage

### Manual Recovery
If automatic processing fails, use the management interface:
1. Go to `/topic-management`
2. Click "Generate Embeddings" to process missing articles
3. Click "Group Topics" to create topic groups
4. Click "Generate Summaries" to create shared summaries

## 📈 Performance Considerations

### Memory Usage
- **Model Loading**: ~100MB for embedding model
- **Batch Processing**: 100 articles per batch (adjustable)
- **Vector Storage**: ~1.5KB per article embedding

### Processing Time
- **Embedding Generation**: ~1-2 seconds per article
- **Topic Grouping**: Depends on number of articles with embeddings
- **Summary Generation**: ~5-10 seconds per topic group

### Database Impact
- **Embeddings**: Add ~1.5KB per article
- **Topic Groups**: Add ~2-5KB per group
- **Cleanup**: Automatic removal of old groups

## 🎯 Benefits

### Zero Maintenance
- **Automatic Setup**: No manual configuration required
- **Self-Healing**: Automatically processes missing data
- **Scheduled Maintenance**: Regular cleanup and updates

### Scalable
- **Background Processing**: Doesn't impact main application
- **Batch Processing**: Handles large datasets efficiently
- **Memory Management**: Configurable batch sizes

### Monitoring
- **Health Checks**: Integrated with main application health
- **Management Interface**: Easy monitoring and manual control
- **Detailed Logging**: Comprehensive operation logs

The system is designed to run completely autonomously while providing full visibility and control when needed.
