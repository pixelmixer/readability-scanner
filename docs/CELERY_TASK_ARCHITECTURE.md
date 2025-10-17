# Celery Task Architecture & Hierarchy Documentation

## Overview
This document provides a comprehensive analysis of all Celery tasks in the News Scanner system, their hierarchies, relationships, and execution patterns.

## Task Queue Architecture

### Queue Structure
```
┌─────────────┬──────────────┬─────────────────────────────────────────────┐
│ Queue       │ Priority     │ Purpose                                      │
├─────────────┼──────────────┼─────────────────────────────────────────────┤
│ high        │ 10           │ Manual user actions (immediate execution)   │
│ normal      │ 5            │ Automatic RSS scanning                      │
│ low         │ 1-3          │ Scheduled maintenance tasks                │
│ ml_queue    │ 1-4          │ ML/AI processing (embeddings, topics)      │
│ llm_queue   │ 2-4          │ LLM processing (summaries)                  │
└─────────────┴──────────────┴─────────────────────────────────────────────┘
```

## Task Categories & Hierarchies

### 1. RSS Scanning Tasks (Queue: normal, low)

#### Primary Scanning Tasks
- **`manual_refresh_source_task`** (Queue: high, Priority: 10)
  - **Purpose**: Manual source refresh from UI
  - **Triggers**: User-initiated via API
  - **Child Tasks**: None (direct execution)
  - **Execution**: Immediate, high priority

- **`scan_single_source_task`** (Queue: normal, Priority: 5)
  - **Purpose**: Scan individual RSS source
  - **Triggers**: 
    - Scheduled via `scheduled_scan_trigger_task`
    - Manual refresh
  - **Child Tasks**: 
    - `generate_article_summary_task` (Priority: 4)
    - `generate_article_embedding` (Priority: 3)
    - `process_new_article` (Priority: 2)
  - **Execution**: Automatic, normal priority

- **`scheduled_scan_trigger_task`** (Queue: low, Priority: 3)
  - **Purpose**: Orchestrate scheduled scans for all sources
  - **Triggers**: Cron schedule (every hour)
  - **Child Tasks**: Multiple `scan_single_source_task` (staggered)
  - **Execution**: Scheduled, low priority

#### Task Flow for RSS Scanning
```
scheduled_scan_trigger_task (low, priority: 3)
    └── scan_single_source_task (normal, priority: 5)
            ├── generate_article_summary_task (llm_queue, priority: 4)
            ├── generate_article_embedding (ml_queue, priority: 3)
            └── process_new_article (ml_queue, priority: 2)
```

### 2. Summary Generation Tasks (Queue: llm_queue)

#### Primary Summary Tasks
- **`generate_article_summary_task`** (Queue: llm_queue, Priority: 4)
  - **Purpose**: Generate summary for single article
  - **Triggers**: 
    - New articles from RSS scanning
    - Manual API calls
    - Summary backlog processing
  - **Child Tasks**: 
    - `generate_summary_embedding_task` (Priority: 4)
  - **Execution**: Automatic/manual, medium priority

- **`process_summary_backlog_task`** (Queue: llm_queue, Priority: 2)
  - **Purpose**: Process articles without summaries
  - **Triggers**: 
    - Scheduled (every 30 minutes)
    - Manual API calls
  - **Child Tasks**: Multiple `generate_article_summary_task`
  - **Execution**: Scheduled/manual, low priority

- **`manual_summary_trigger_task`** (Queue: llm_queue, Priority: 5)
  - **Purpose**: Manual summary generation trigger
  - **Triggers**: User-initiated via API
  - **Child Tasks**: `process_summary_backlog_task`
  - **Execution**: Manual, high priority

#### Summary Embedding Tasks
- **`generate_summary_embedding_task`** (Queue: ml_queue, Priority: 4)
  - **Purpose**: Generate embeddings from summaries
  - **Triggers**: After successful summary generation
  - **Child Tasks**: None
  - **Execution**: Automatic, medium priority

- **`batch_generate_summary_embeddings_task`** (Queue: ml_queue, Priority: 2)
  - **Purpose**: Batch process summary embeddings
  - **Triggers**: Manual API calls
  - **Child Tasks**: Multiple `generate_summary_embedding_task`
  - **Execution**: Manual, low priority

### 3. ML/AI Processing Tasks (Queue: ml_queue)

#### Article Embedding Tasks
- **`generate_article_embedding`** (Queue: ml_queue, Priority: 3)
  - **Purpose**: Generate embeddings for article content
  - **Triggers**: New articles from RSS scanning
  - **Child Tasks**: None
  - **Execution**: Automatic, medium priority

- **`batch_generate_embeddings`** (Queue: ml_queue, Priority: 3)
  - **Purpose**: Batch process article embeddings
  - **Triggers**: Manual API calls
  - **Child Tasks**: Multiple `generate_article_embedding`
  - **Execution**: Manual, medium priority

#### Topic Analysis Tasks
- **`process_new_article`** (Queue: ml_queue, Priority: 2)
  - **Purpose**: Process new article for topic analysis
  - **Triggers**: New articles from RSS scanning
  - **Child Tasks**: None
  - **Execution**: Automatic, low priority

- **`group_articles_by_topics`** (Queue: ml_queue, Priority: 2)
  - **Purpose**: Group articles by topic similarity
  - **Triggers**: Manual API calls
  - **Child Tasks**: None
  - **Execution**: Manual, low priority

- **`generate_shared_summaries`** (Queue: llm_queue, Priority: 2)
  - **Purpose**: Generate summaries for topic groups
  - **Triggers**: Manual API calls
  - **Child Tasks**: None
  - **Execution**: Manual, low priority

- **`full_topic_analysis_pipeline`** (Queue: ml_queue, Priority: 1)
  - **Purpose**: Complete topic analysis pipeline
  - **Triggers**: Scheduled (weekly)
  - **Child Tasks**: Multiple ML tasks
  - **Execution**: Scheduled, lowest priority

### 4. Daily Topics Tasks (Queue: llm_queue)

- **`generate_daily_topics_task`** (Queue: llm_queue, Priority: 2)
  - **Purpose**: Generate daily topic summaries
  - **Triggers**: Scheduled (hourly)
  - **Child Tasks**: None
  - **Execution**: Scheduled, low priority

- **`regenerate_daily_topics_task`** (Queue: high, Priority: 10)
  - **Purpose**: Manual regeneration of daily topics
  - **Triggers**: User-initiated via API
  - **Child Tasks**: None
  - **Execution**: Manual, highest priority

### 5. Maintenance Tasks (Queue: low, high)

#### Data Cleanup Tasks
- **`backfill_publication_dates_task`** (Queue: low, Priority: 1)
  - **Purpose**: Backfill missing publication dates
  - **Triggers**: Manual API calls
  - **Child Tasks**: None
  - **Execution**: Manual, lowest priority

- **`cleanup_old_date_fields_task`** (Queue: high, Priority: 10)
  - **Purpose**: Clean up old date field formats
  - **Triggers**: Manual API calls
  - **Child Tasks**: None
  - **Execution**: Manual, highest priority

#### Reddit Integration Tasks
- **`reddit_backfill_task`** (Queue: low, Priority: 1)
  - **Purpose**: Backfill Reddit data
  - **Triggers**: Manual API calls
  - **Child Tasks**: None
  - **Execution**: Manual, lowest priority

- **`reddit_backfill_stats_task`** (Queue: low, Priority: 1)
  - **Purpose**: Generate Reddit backfill statistics
  - **Triggers**: Manual API calls
  - **Child Tasks**: None
  - **Execution**: Manual, lowest priority

## Scheduled Tasks (Beat Schedule)

### Automatic Execution Schedule
```
┌─────────────────────────────────┬──────────────┬─────────────────────────┐
│ Task                            │ Schedule     │ Queue & Priority         │
├─────────────────────────────────┼──────────────┼─────────────────────────┤
│ scheduled-source-scan           │ Every hour   │ low, priority: 3        │
│ process-summary-backlog         │ Every 30 min │ low, priority: 2        │
│ weekly-topic-analysis           │ Sunday 2 AM  │ low, priority: 1        │
│ hourly-daily-topics-update      │ Every hour   │ low, priority: 2        │
└─────────────────────────────────┴──────────────┴─────────────────────────┘
```

## Task Execution Patterns

### 1. Automatic RSS Scanning Flow
```
Hourly Schedule:
scheduled_scan_trigger_task
    └── scan_single_source_task (per source, staggered)
            ├── generate_article_summary_task
            │   └── generate_summary_embedding_task
            ├── generate_article_embedding
            └── process_new_article
```

### 2. Manual Summary Generation Flow
```
User Trigger:
manual_summary_trigger_task
    └── process_summary_backlog_task
            └── generate_article_summary_task (per article)
                    └── generate_summary_embedding_task
```

### 3. Topic Analysis Flow
```
Weekly Schedule:
full_topic_analysis_pipeline
    ├── batch_generate_embeddings
    ├── group_articles_by_topics
    └── generate_shared_summaries
```

## Task Consistency Analysis

### ✅ Consistent Execution Patterns

1. **Queue Assignment**: All tasks use correct queues based on their purpose
2. **Priority Ordering**: Tasks follow logical priority hierarchy
3. **Child Task Triggering**: Parent tasks properly trigger child tasks
4. **Error Handling**: All tasks have retry logic and error handling
5. **Database Operations**: All tasks use proper database connection management

### ✅ Manual vs Scheduled Consistency

1. **Same Task Functions**: Manual and scheduled tasks use identical task functions
2. **Same Parameters**: Both execution modes use same parameters and logic
3. **Same Queues**: Manual triggers use same queues as scheduled tasks
4. **Same Priorities**: Priority levels consistent across execution modes

### ✅ Task Dependencies

1. **Proper Sequencing**: Tasks execute in correct order based on dependencies
2. **No Circular Dependencies**: Clean dependency graph
3. **Graceful Degradation**: System continues if individual tasks fail
4. **Resource Management**: Proper queue separation prevents resource conflicts

## Recommendations

### 1. Task Monitoring
- Monitor queue depths for each queue type
- Track task execution times and failure rates
- Set up alerts for stuck or failed tasks

### 2. Performance Optimization
- Consider increasing worker count for high-volume queues
- Monitor memory usage for ML tasks
- Implement task result caching where appropriate

### 3. Error Handling
- All tasks have retry logic (max 3 retries)
- Failed tasks are logged with full context
- Dead letter queue handling for permanently failed tasks

### 4. Scalability
- Queue separation allows independent scaling
- Worker processes can be scaled per queue type
- Task priorities ensure critical tasks execute first
