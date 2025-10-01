# Date Field Cleanup Guide

## Overview

This guide explains the one-time cleanup task created to standardize date field names in the MongoDB documents collection.

## Problem

The system was using inconsistent field names for publication dates:
- `publication date` (with space) - old field name
- `publication_date` (with underscore) - new standardized field name  
- `publishedTime` - deprecated field name

This inconsistency caused confusion and potential data access issues.

## Solution

### 1. New Celery Task: `cleanup_old_date_fields_task`

**Location**: `news-scanner/celery_app/tasks.py`

**Purpose**: One-time migration task that:
1. Finds documents with `publication date` field but no `publication_date` field
2. Copies `publication date` to `publication_date` if the latter is empty
3. Removes `publication date` and `publishedTime` fields

**Usage**:
```python
# Queue the task
from celery_app.tasks import cleanup_old_date_fields_task
task = cleanup_old_date_fields_task.delay(batch_size=50)
```

### 2. API Endpoint: `/scan/cleanup-date-fields`

**Location**: `news-scanner/api/routes/scan.py`

**Purpose**: HTTP endpoint to trigger the cleanup task

**Usage**:
```bash
curl -X POST "http://localhost:8000/scan/cleanup-date-fields?batch_size=50"
```

**Response**:
```json
{
  "success": true,
  "message": "Date field cleanup task queued successfully",
  "task_id": "task-uuid-here",
  "batch_size": 50,
  "status": "queued",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 3. Updated Article Ingestion

**Location**: `news-scanner/scanner/scanner.py`

**Changes**:
- Updated line 187 to use `publication_date` instead of `publication date`
- Ensures new articles only use the standardized field name

### 4. Updated Database Operations

**Location**: `news-scanner/database/articles.py`

**Changes**:
- Removed field mapping between old and new field names
- Updated all indexes to use `publication_date`
- Updated all queries to use `publication_date`
- Removed references to `publication date` field

## Running the Cleanup

### Option 1: Via API (Recommended)
```bash
# Start the services
docker-compose up -d

# Trigger the cleanup task
curl -X POST "http://localhost:8000/scan/cleanup-date-fields?batch_size=50"

# Check task status (replace TASK_ID with actual task ID)
curl "http://localhost:8000/celery/task/TASK_ID/status"
```

### Option 2: Direct Celery Task
```python
from celery_app.tasks import cleanup_old_date_fields_task

# Queue the task
task = cleanup_old_date_fields_task.delay(batch_size=50)

# Check result
result = task.get()
print(result)
```

### Option 3: Test Script
```bash
cd news-scanner
python test_date_cleanup.py
```

## Monitoring Progress

The task provides detailed logging:
- Total documents found with old fields
- Progress updates during processing
- Number of fields migrated and removed
- Error reporting for failed operations

## Safety Features

- **Batch Processing**: Processes documents in configurable batches (default: 50)
- **Error Handling**: Continues processing even if individual documents fail
- **Data Preservation**: Only migrates data, never deletes without copying
- **Rollback Safe**: Original data is preserved until explicitly removed

## Expected Results

After running the cleanup:
- All documents will use `publication_date` field consistently
- Old `publication date` and `publishedTime` fields will be removed
- Database indexes will be optimized for the new field name
- New article ingestion will only use standardized field names

## Verification

To verify the cleanup was successful:

```python
from database.articles import article_repository
from database.connection import db_manager

async def verify_cleanup():
    await db_manager.connect()
    collection = article_repository.collection
    
    # Check for old fields (should be 0)
    old_fields = await collection.count_documents({"publication date": {"$exists": True}})
    published_time = await collection.count_documents({"publishedTime": {"$exists": True}})
    
    # Check for new field (should be > 0)
    new_field = await collection.count_documents({"publication_date": {"$exists": True}})
    
    print(f"Documents with 'publication date': {old_fields}")
    print(f"Documents with 'publishedTime': {published_time}")
    print(f"Documents with 'publication_date': {new_field}")
    
    await db_manager.disconnect()
```

## Notes

- This is a **one-time migration task** - run it once to clean up existing data
- Future article ingestion will automatically use the correct field names
- The task is idempotent - running it multiple times is safe
- Consider running during low-traffic periods for better performance
