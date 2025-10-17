# Celery Task Hierarchy Diagram

## Task Flow Visualization

### 1. RSS Scanning Pipeline
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SCHEDULED RSS SCANNING                            │
└─────────────────────────────────────────────────────────────────────────────┘

scheduled_scan_trigger_task (low, priority: 3)
    │
    ├── scan_single_source_task (normal, priority: 5) [Source 1]
    │   │
    │   ├── generate_article_summary_task (llm_queue, priority: 4)
    │   │   │
    │   │   └── generate_summary_embedding_task (ml_queue, priority: 4)
    │   │
    │   ├── generate_article_embedding (ml_queue, priority: 3)
    │   │
    │   └── process_new_article (ml_queue, priority: 2)
    │
    ├── scan_single_source_task (normal, priority: 5) [Source 2]
    │   │
    │   └── [Same child tasks as above]
    │
    └── scan_single_source_task (normal, priority: 5) [Source N]
        │
        └── [Same child tasks as above]
```

### 2. Manual Summary Generation Pipeline
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MANUAL SUMMARY GENERATION                             │
└─────────────────────────────────────────────────────────────────────────────┘

manual_summary_trigger_task (llm_queue, priority: 5)
    │
    └── process_summary_backlog_task (llm_queue, priority: 2)
        │
        ├── generate_article_summary_task (llm_queue, priority: 4) [Article 1]
        │   │
        │   └── generate_summary_embedding_task (ml_queue, priority: 4)
        │
        ├── generate_article_summary_task (llm_queue, priority: 4) [Article 2]
        │   │
        │   └── generate_summary_embedding_task (ml_queue, priority: 4)
        │
        └── generate_article_summary_task (llm_queue, priority: 4) [Article N]
            │
            └── generate_summary_embedding_task (ml_queue, priority: 4)
```

### 3. Topic Analysis Pipeline
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TOPIC ANALYSIS                                    │
└─────────────────────────────────────────────────────────────────────────────┘

full_topic_analysis_pipeline (ml_queue, priority: 1)
    │
    ├── batch_generate_embeddings (ml_queue, priority: 3)
    │   │
    │   └── generate_article_embedding (ml_queue, priority: 3) [per article]
    │
    ├── group_articles_by_topics (ml_queue, priority: 2)
    │
    └── generate_shared_summaries (llm_queue, priority: 2)
```

### 4. Daily Topics Pipeline
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DAILY TOPICS                                     │
└─────────────────────────────────────────────────────────────────────────────┘

generate_daily_topics_task (llm_queue, priority: 2)
    │
    └── [Internal processing - no child tasks]

regenerate_daily_topics_task (high, priority: 10)
    │
    └── [Internal processing - no child tasks]
```

## Queue Distribution

### Task Distribution by Queue
```
┌─────────────┬──────────────────────────────────────────────────────────────┐
│ Queue       │ Tasks                                                        │
├─────────────┼──────────────────────────────────────────────────────────────┤
│ high        │ manual_refresh_source_task                                   │
│             │ cleanup_old_date_fields_task                                 │
│             │ regenerate_daily_topics_task                                 │
├─────────────┼──────────────────────────────────────────────────────────────┤
│ normal      │ scan_single_source_task                                     │
│             │ scan_article_task                                           │
├─────────────┼──────────────────────────────────────────────────────────────┤
│ low         │ scheduled_scan_trigger_task                                  │
│             │ backfill_publication_dates_task                              │
│             │ reddit_backfill_task                                         │
│             │ reddit_backfill_stats_task                                   │
├─────────────┼──────────────────────────────────────────────────────────────┤
│ ml_queue    │ generate_article_embedding                                  │
│             │ batch_generate_embeddings                                    │
│             │ group_articles_by_topics                                     │
│             │ process_new_article                                          │
│             │ full_topic_analysis_pipeline                                 │
│             │ generate_summary_embedding_task                              │
│             │ batch_generate_summary_embeddings_task                       │
├─────────────┼──────────────────────────────────────────────────────────────┤
│ llm_queue   │ generate_article_summary_task                               │
│             │ process_summary_backlog_task                                 │
│             │ manual_summary_trigger_task                                  │
│             │ generate_daily_topics_task                                   │
│             │ generate_shared_summaries                                    │
└─────────────┴──────────────────────────────────────────────────────────────┘
```

## Priority Hierarchy

### Task Priority Levels
```
Priority 10 (Highest):
├── manual_refresh_source_task
├── cleanup_old_date_fields_task
└── regenerate_daily_topics_task

Priority 5 (High):
├── scan_single_source_task
└── manual_summary_trigger_task

Priority 4 (Medium):
├── generate_article_summary_task
├── generate_summary_embedding_task
└── process_new_article

Priority 3 (Medium-Low):
├── scheduled_scan_trigger_task
├── generate_article_embedding
└── batch_generate_embeddings

Priority 2 (Low):
├── process_summary_backlog_task
├── group_articles_by_topics
├── generate_shared_summaries
├── generate_daily_topics_task
└── batch_generate_summary_embeddings_task

Priority 1 (Lowest):
├── backfill_publication_dates_task
├── reddit_backfill_task
├── reddit_backfill_stats_task
└── full_topic_analysis_pipeline
```

## Execution Timing

### Scheduled Tasks Timeline
```
Hour 0:00  ──────────────────────────────────────────────────────────────
          │ scheduled-source-scan (every hour)
          │ hourly-daily-topics-update (every hour)
          │
Hour 0:30  ──────────────────────────────────────────────────────────────
          │ process-summary-backlog (every 30 minutes)
          │
Hour 1:00  ──────────────────────────────────────────────────────────────
          │ scheduled-source-scan (every hour)
          │ hourly-daily-topics-update (every hour)
          │
Hour 1:30  ──────────────────────────────────────────────────────────────
          │ process-summary-backlog (every 30 minutes)
          │
Hour 2:00  ──────────────────────────────────────────────────────────────
          │ scheduled-source-scan (every hour)
          │ hourly-daily-topics-update (every hour)
          │
...continues every hour...

Sunday 2:00 AM ──────────────────────────────────────────────────────────
               │ weekly-topic-analysis (weekly)
```

## Task Dependencies Matrix

### Dependency Relationships
```
┌─────────────────────────────────┬─────────────────────────────────────────┐
│ Parent Task                     │ Child Tasks                            │
├─────────────────────────────────┼─────────────────────────────────────────┤
│ scheduled_scan_trigger_task     │ scan_single_source_task (multiple)     │
│ scan_single_source_task         │ generate_article_summary_task          │
│                                 │ generate_article_embedding              │
│                                 │ process_new_article                     │
│ generate_article_summary_task    │ generate_summary_embedding_task        │
│ manual_summary_trigger_task     │ process_summary_backlog_task            │
│ process_summary_backlog_task    │ generate_article_summary_task (multiple)│
│ full_topic_analysis_pipeline    │ batch_generate_embeddings              │
│                                 │ group_articles_by_topics                │
│                                 │ generate_shared_summaries               │
│ batch_generate_embeddings       │ generate_article_embedding (multiple)  │
│ batch_generate_summary_embeddings│ generate_summary_embedding_task (multiple)│
└─────────────────────────────────┴─────────────────────────────────────────┘
```

## Error Handling & Retry Logic

### Retry Configuration
```
┌─────────────────────────────────┬─────────────────────────────────────────┐
│ Task Type                      │ Retry Configuration                     │
├─────────────────────────────────┼─────────────────────────────────────────┤
│ Manual Tasks                    │ Max 2 retries, 30s delay               │
│ RSS Scanning Tasks              │ Max 3 retries, exponential backoff     │
│ Summary Tasks                   │ Max 2 retries, 60s delay               │
│ ML Tasks                        │ Max 3 retries, 60s delay               │
│ Maintenance Tasks               │ Max 3 retries, 120s delay               │
└─────────────────────────────────┴─────────────────────────────────────────┘
```

## Resource Requirements

### Queue Resource Allocation
```
┌─────────────┬──────────────────────────────────────────────────────────────┐
│ Queue       │ Resource Requirements                                        │
├─────────────┼──────────────────────────────────────────────────────────────┤
│ high        │ Fast execution, low latency                                 │
│ normal      │ Moderate resources, steady processing                      │
│ low         │ Background processing, can be delayed                      │
│ ml_queue    │ High CPU/memory for ML processing                          │
│ llm_queue   │ High memory for LLM processing, rate limiting             │
└─────────────┴──────────────────────────────────────────────────────────────┘
```
