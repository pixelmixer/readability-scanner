# Hug Component (Python API) Documentation

## Overview
The Hug component is a Python-based REST API built with the Hug framework. It provides data export, machine learning utilities, and advanced analytics for the readability analysis system.

## Purpose
This component serves as:
- **Data Export Service**: Generates training/test datasets from MongoDB
- **Analytics Engine**: Provides advanced data aggregation and analysis
- **ML Pipeline**: Prepares data for machine learning models
- **File Generation**: Creates downloadable archives of processed data

## Container Configuration
- **Base Image**: `python:3.10.15-alpine3.20`
- **Port**: `3839:8000` (accessible at `localhost:3839`)
- **Network**: `readable` (internal Docker network)
- **Dependencies**: MongoDB access, Node.js for additional tooling

## Core Dependencies
```python
hug           # Web API framework
pymongo       # MongoDB driver
pandas        # Data manipulation
sklearn       # Machine learning library
numpy<2.0     # Numerical computing
```

## API Endpoints

### 1. **Data Export & File Generation**

#### `/export`
- **Method**: GET
- **Purpose**: Export specific date range of articles
- **Functionality**:
  - Filters articles by publication date (March 29 - April 5, 2021)
  - Extracts URL and Host information
  - Returns filtered dataset

#### `/create_zip`
- **Method**: GET
- **Returns**: `data.tar.gz` file
- **Purpose**: Creates compressed archive of training data
- **Functionality**:
  - Packages `./data/` directory into tar.gz format
  - Returns downloadable archive file

#### `/get_zip`
- **Method**: GET  
- **Returns**: Existing `data.tar.gz` file
- **Purpose**: Downloads previously created data archive

### 2. **Machine Learning Data Preparation**

#### `/generate_files`
- **Method**: GET
- **Returns**: HTML report
- **Purpose**: Generates ML training/test datasets
- **Functionality**:
  - Extracts articles with associated reliability scores
  - Creates directory structure for ML training:
    ```
    data/
    ├── train/
    │   ├── [reliability_score]/
    │   │   ├── 1.txt
    │   │   ├── 2.txt
    │   │   └── ...
    └── test/
        ├── [reliability_score]/
        │   ├── 1.txt
        │   ├── 2.txt
        │   └── ...
    ```
  - Splits data by reliability classification
  - Writes cleaned article content to individual text files
  - Provides performance metrics and statistics

#### Data Processing Pipeline:
1. **MongoDB Aggregation**: Joins articles with URL metadata
2. **Classification**: Groups by reliability score
3. **Content Extraction**: Uses cleaned article text
4. **File Generation**: Creates individual text files per article
5. **Performance Tracking**: Reports processing time and statistics

### 3. **Analytics & Insights**

#### `/wordcloud`
- **Method**: GET
- **Purpose**: Word frequency analysis
- **Functionality**:
  - Aggregates word usage across all articles
  - Counts word frequency
  - Returns top 5 most common words
  - Uses MongoDB aggregation pipeline for processing

### 4. **External AI Integration**

#### `/summarize`
- **Method**: POST
- **Parameters**: 
  - `prompt`: Text to summarize
  - `history`: Conversation context (optional)
- **Purpose**: AI-powered text summarization
- **Functionality**:
  - Connects to external AI service (`192.168.86.32:5000`)
  - Uses advanced language model for text generation
  - Configurable parameters for fine-tuning output
  - Supports conversation history and context

#### AI Configuration:
```python
{
    'max_new_tokens': 250,
    'temperature': 0.7,
    'top_p': 0.1,
    'repetition_penalty': 1.18,
    'top_k': 40,
    'instruction_template': 'Vicuna-v1.1'
}
```

### 5. **Data Analysis**

#### MongoDB Aggregation Features:
- **Date Range Filtering**: Precise publication date filtering
- **Source Analysis**: Groups data by news source
- **Metadata Enrichment**: Joins articles with source reliability data
- **Statistical Analysis**: Pandas integration for advanced analytics

## Database Operations

### Collections Used:
- **documents**: Main article storage with readability metrics
- **urls**: RSS feed sources with reliability metadata

### Key Aggregation Patterns:
```python
# Filter by date and source validity
{
    '$match': {
        'publication_date': {'$gte': start_date, '$lte': end_date},
        'origin': {'$ne': None}
    }
}

# Join with source metadata
{
    '$lookup': {
        'from': 'urls',
        'localField': 'origin', 
        'foreignField': 'url',
        'as': 'host'
    }
}
```

## File System Operations

### Data Directory Structure:
```
hug/
├── data/
│   ├── train/
│   │   └── [classification]/
│   │       └── [article_id].txt
│   └── test/
│       └── [classification]/
│           └── [article_id].txt
├── data.tar.gz
└── hug.py
```

### Archive Creation:
- **Compression**: gzip compression for efficiency
- **Directory Inclusion**: Preserves directory structure
- **Error Handling**: Graceful handling of file operations

## Performance Features

### Caching & Optimization:
- **File Existence Checks**: Prevents duplicate file creation
- **Performance Monitoring**: Tracks processing time with `time.perf_counter()`
- **Batch Processing**: Efficient handling of large datasets
- **Memory Management**: Pandas DataFrame optimization

### Scalability:
- **MongoDB Aggregation**: Server-side processing for large datasets
- **Streaming**: File-based output for memory efficiency
- **Parallel Processing**: Ready for multi-threading enhancements

## Integration Points

### With Main Application:
- **Shared Database**: Common MongoDB instance
- **Data Consistency**: Uses same document structure
- **Reliability Metadata**: Leverages URL classification data

### With External Services:
- **AI Service**: External language model integration
- **Download Interface**: Web-accessible file downloads
- **API Consumption**: RESTful endpoints for data access

## Key Features

1. **ML-Ready Data**: Automated dataset preparation for machine learning
2. **Flexible Export**: Multiple export formats and filtering options
3. **Advanced Analytics**: Pandas-powered statistical analysis
4. **AI Integration**: External language model connectivity
5. **Performance Monitoring**: Built-in timing and statistics
6. **Web Interface**: HTML-based reporting and visualization
7. **Archive Management**: Automated compression and download
8. **Modular Design**: Easy to extend with additional endpoints

## Usage Examples

```bash
# Generate ML datasets
curl http://localhost:3839/generate_files

# Download data archive  
curl -O http://localhost:3839/get_zip

# Word frequency analysis
curl http://localhost:3839/wordcloud

# Summarize text
curl -X POST http://localhost:3839/summarize \
  -d "prompt=Your text here"
```
