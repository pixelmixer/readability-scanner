# Main Application (Node.js) Documentation

## Overview
The main application is a **News Readability Analysis System** built with Node.js and Express. It automatically crawls news articles from RSS feeds, analyzes their readability using multiple readability metrics, and stores the results in a MongoDB database.

## Core Functionality

### 1. **Scheduled RSS Feed Crawling**
- **Cron-based scheduling**: Uses `node-cron` with configurable intervals (defined in `.env` as `INTERVAL`)
- **RSS feed parsing**: Parses RSS feeds using `rss-parser` library
- **URL management**: Stores RSS feed URLs in MongoDB `urls` collection
- **Automatic crawling**: Runs through all stored RSS feeds on schedule

### 2. **Content Processing Pipeline**
1. **Content Extraction**: Sends article URLs to readability service (`http://readability:3000`)
2. **Text Cleaning**: Strips HTML tags and normalizes whitespace
3. **Readability Analysis**: Calculates multiple readability metrics
4. **Database Storage**: Stores results in MongoDB `documents` collection

### 3. **Readability Metrics Calculated**
- **Flesch Reading Ease**: Measures text difficulty (0-100 scale)
- **Flesch-Kincaid Grade Level**: Grade level required to understand text
- **SMOG Index**: Simple Measure of Gobbledygook
- **Dale-Chall Readability**: Uses list of common words
- **Coleman-Liau Index**: Character-based readability metric
- **Gunning Fog Index**: Measures text complexity
- **Spache Readability**: For elementary school texts
- **Automated Readability Index**: Character and sentence based

### 4. **Text Statistics**
- Word count, sentence count, paragraph count
- Character count and syllable count
- Complex polysyllabic word analysis
- Average word syllables

### 5. **Web Dashboard**
- **Daily Reports**: `/daily` - Aggregated readability data by date range
- **Trend Graphs**: `/graph` - Visual trends over time using Chart.js
- **Source Analysis**: `/source/:origin` - Individual news source analysis
- **Data Export**: `/export` - CSV/JSON export functionality
- **RSS Management**: `/add-url` - Add new RSS feeds

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Scan single URL (`?url=https://example.com`) |
| `/daily` | GET | Daily readability report with date filtering |
| `/graph` | GET | Trend visualization data |
| `/source/:origin` | GET | Individual news source analysis |
| `/export` | GET | Export data as CSV or JSON |
| `/add-url` | GET | Add RSS feed URL to monitoring list |

## Configuration

### Environment Variables (`.env`)
```bash
INTERVAL=0 12 * * SUN-SAT  # Cron schedule (daily at noon)
```

### Database Collections
- **documents**: Stores analyzed articles with readability metrics
- **urls**: Stores RSS feed URLs for monitoring

## Dependencies

### Core Libraries
- **express**: Web framework
- **mongodb**: Database driver
- **rss-parser**: RSS feed parsing
- **node-cron**: Scheduled tasks
- **node-fetch**: HTTP requests

### Readability Libraries
- **flesch**, **flesch-kincaid**: Readability calculations
- **smog-formula**, **dale-chall-formula**: Additional metrics
- **gunning-fog**, **spache-formula**: Text complexity
- **automated-readability**, **coleman-liau**: Alternative metrics
- **countable**: Text statistics
- **syllable**: Syllable counting

### Utility Libraries
- **striptags**: HTML tag removal
- **html-to-text**: HTML to text conversion
- **moment**: Date manipulation
- **json2csv**: CSV export functionality
- **ejs**: Template engine for web views

## Service Dependencies
- **MongoDB**: Database storage (port 27017)
- **Readability Service**: Content extraction (port 3000)
- **RSS-Bridge**: Custom RSS feeds (port 3939)

## Data Flow
1. **Scheduler triggers** → `scanFeeds()`
2. **Fetch RSS feeds** → Parse article URLs
3. **Send to readability service** → Extract main content
4. **Process content** → Calculate readability metrics
5. **Store in MongoDB** → Update/insert article data
6. **Web dashboard** → Display analytics and trends

## Key Features
- **Upsert logic**: Prevents duplicate articles using URL as key
- **Error handling**: Graceful handling of failed requests
- **Configurable scheduling**: Flexible cron-based timing
- **Multi-format export**: JSON and CSV data export
- **Visual analytics**: Chart.js-powered trend graphs
- **Date filtering**: Historical data analysis capabilities
