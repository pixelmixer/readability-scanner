# Topic Analysis System

This document describes the topic analysis system that groups news articles by similarity and generates shared summaries.

## Overview

The topic analysis system uses vector embeddings to identify articles that discuss similar topics, then groups them together and generates shared summaries. This enables:

1. **Similar Article Discovery**: Find articles about the same topic when reading any article
2. **Topic Grouping**: Automatically group related articles together
3. **Shared Summaries**: Generate comprehensive summaries that combine information from multiple related articles

## Architecture

```
Articles → Embeddings → Vector Similarity → Topic Groups → Shared Summaries
```

### Components

- **Vector Service** (`services/vector_service.py`): Generates and manages article embeddings
- **Topic Service** (`services/topic_service.py`): Groups articles and generates shared summaries
- **Celery Tasks** (`celery_app/jobs/topic_analysis_jobs.py`): Background processing for embeddings and grouping
- **API Routes** (`api/routes/topic_routes.py`): REST API for frontend integration
- **Frontend** (`templates/pages/article_viewer.html`): Web interface for finding similar articles

## Setup

### 1. Install Dependencies

The system requires additional Python packages for vector processing:

```bash
pip install sentence-transformers scikit-learn torch transformers
```

### 2. Initialize the System

Run the setup script to generate embeddings for existing articles:

```bash
# Full pipeline (recommended for first run)
python scripts/topic_analysis_setup.py full-pipeline

# Or run steps individually:
python scripts/topic_analysis_setup.py embeddings --batch-size 50
python scripts/topic_analysis_setup.py group-topics --similarity-threshold 0.75
python scripts/topic_analysis_setup.py summaries
```

### 3. Check Status

View system statistics:

```bash
python scripts/topic_analysis_setup.py stats
```

## Usage

### API Endpoints

#### Get Similar Articles
```http
GET /api/topics/similar/{article_url}?limit=10&similarity_threshold=0.6
```

#### Get Article Topic Groups
```http
GET /api/topics/article/{article_url}/topics
```

#### Get All Topic Groups
```http
GET /api/topics/groups?limit=50
```

#### Get Topic Group Details
```http
GET /api/topics/groups/{topic_id}
```

#### Get Statistics
```http
GET /api/topics/stats
```

### Frontend Interface

Access the article viewer at: `http://localhost:30005/article-viewer`

Features:
- Enter any article URL to find similar articles
- View similarity scores and previews
- See topic groups and shared summaries
- Click through to view full articles

### Celery Tasks

#### Process New Article
```python
from celery_app.tasks import process_new_article
result = await process_new_article.delay("https://example.com/article")
```

#### Generate Embeddings for All Articles
```python
from celery_app.tasks import batch_generate_embeddings
result = await batch_generate_embeddings.delay(batch_size=100)
```

#### Group Articles by Topics
```python
from celery_app.tasks import group_articles_by_topics
result = await group_articles_by_topics.delay(similarity_threshold=0.75, min_group_size=2)
```

#### Generate Shared Summaries
```python
from celery_app.tasks import generate_shared_summaries
result = await generate_shared_summaries.delay()
```

#### Full Pipeline
```python
from celery_app.tasks import full_topic_analysis_pipeline
result = await full_topic_analysis_pipeline.delay()
```

## Configuration

### Vector Service Settings

The vector service uses the `all-MiniLM-L6-v2` model by default. You can modify this in `services/vector_service.py`:

```python
vector_service = VectorSimilarityService(model_name="all-MiniLM-L6-v2")
```

### Similarity Thresholds

- **Display threshold**: 0.6 (for showing similar articles in UI)
- **Grouping threshold**: 0.75 (for creating topic groups)
- **Minimum group size**: 2 articles

### Batch Processing

- **Embedding generation**: Process 50-100 articles per batch
- **Topic grouping**: Process all articles with embeddings
- **Summary generation**: Process all topic groups

## Database Schema

### Documents Collection (Enhanced)
```json
{
  "url": "https://example.com/article",
  "title": "Article Title",
  "content": "Article content...",
  "Cleaned Data": "Cleaned content...",
  "embedding": [0.1, -0.2, 0.3, ...],  // 384-dimensional vector
  "embedding_updated_at": "2024-01-01T12:00:00Z",
  "embedding_model": "all-MiniLM-L6-v2"
}
```

### Article Topics Collection (New)
```json
{
  "topic_id": "topic_1",
  "articles": [...],  // Array of article documents
  "similarity_scores": [0.95, 0.87, 0.82, ...],
  "article_count": 5,
  "shared_summary": "Combined summary of all articles...",
  "summary_generated_at": "2024-01-01T12:00:00Z",
  "created_at": "2024-01-01T12:00:00Z"
}
```

## Performance Considerations

### Memory Usage
- Each embedding is 384 dimensions (1.5KB per article)
- Model loading requires ~100MB RAM
- Batch processing helps manage memory usage

### Processing Time
- Embedding generation: ~1-2 seconds per article
- Topic grouping: Depends on number of articles with embeddings
- Summary generation: ~5-10 seconds per topic group

### Storage
- Embeddings add ~1.5KB per article
- Topic groups add ~2-5KB per group
- Consider cleanup of old topic groups periodically

## Monitoring

### Health Check
The system status is included in the main health check:
```http
GET /health
```

### Celery Monitoring
Use Flower to monitor task progress:
```http
http://localhost:30006
```

### Logs
Check container logs for detailed information:
```bash
docker-compose logs -f news-scanner
docker-compose logs -f celery-worker
```

## Troubleshooting

### Common Issues

1. **Out of Memory**: Reduce batch size for embedding generation
2. **Slow Processing**: Check if GPU is available for model inference
3. **No Similar Articles**: Lower similarity threshold or check embedding quality
4. **Missing Summaries**: Ensure summary service is working properly

### Debug Commands

```bash
# Check embedding coverage
python scripts/topic_analysis_setup.py stats

# Test with specific article
curl "http://localhost:30005/api/topics/similar/https://example.com/article"

# Check Celery task status
curl "http://localhost:30006/api/workers"
```

## Future Enhancements

1. **GPU Support**: Use CUDA for faster embedding generation
2. **Incremental Updates**: Only process new/changed articles
3. **Topic Clustering**: Use more sophisticated clustering algorithms
4. **Real-time Updates**: WebSocket updates for new similar articles
5. **Advanced Summarization**: Use larger language models for better summaries
6. **Topic Evolution**: Track how topics change over time
7. **Multi-language Support**: Handle articles in different languages
