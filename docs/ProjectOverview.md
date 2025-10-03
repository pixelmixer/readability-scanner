# News Readability Analysis System - Project Overview

## Project Description
A comprehensive **automated news analysis system** that crawls news articles from RSS feeds, performs detailed readability analysis using multiple metrics, and provides web-based analytics and data export capabilities.

## Core Functionality
- **Automated RSS Crawling**: Scheduled monitoring of news RSS feeds
- **Custom RSS Generation**: Creates RSS feeds for sites that don't provide them
- **Content Extraction**: Intelligent extraction of main article content
- **Readability Analysis**: Multiple readability metrics (Flesch, SMOG, etc.)
- **Data Storage**: MongoDB-based persistent storage
- **Web Analytics**: Interactive dashboards and trend visualization
- **ML Data Export**: Prepares datasets for machine learning applications

## System Architecture

### Component Overview
```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network: readable               │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ RSS-Bridge   │  │ Readability  │  │ Main App        │  │
│  │ (RSS Gen)    │  │ (Content     │  │ (Crawler +      │  │
│  │ :30002       │  │ Extract)     │  │ Analytics)      │  │
│  └──────────────┘  │ :3000        │  │ :4912           │  │
│                     └──────────────┘  └─────────────────┘  │
│                                                ▲             │
│  ┌──────────────┐  ┌──────────────────────────┼───────────┐ │
│  │ Hug API      │  │           MongoDB        │           │ │
│  │ (Python ML)  │◄─┤         (Database)       │           │ │
│  │ :30003       │  │          :30001          │           │ │
│  └──────────────┘  └──────────────────────────┼───────────┘ │
│                                                ▼             │
└─────────────────────────────────────────────────────────────┘
                                                ▼
                                    E:\NewsDatabase (Volume)
```

## Technology Stack

### **Main Application (Node.js)**
- **Framework**: Express.js web server
- **Scheduling**: Node-cron for automated tasks
- **RSS Parsing**: RSS-parser library
- **Database**: MongoDB with native driver
- **Readability**: Multiple specialized libraries
- **Templating**: EJS for web views
- **Charts**: Chart.js for data visualization

### **RSS-Bridge (PHP)**
- **Framework**: RSS-Bridge open source project
- **Purpose**: Generate RSS feeds from non-RSS websites
- **Custom Bridges**: AP News, Reuters implementations
- **Caching**: Built-in content caching system

### **Hug Component (Python)**
- **Framework**: Hug API framework
- **Data Processing**: Pandas for analysis
- **ML Libraries**: Scikit-learn, NumPy
- **Database**: PyMongo for MongoDB access
- **Export**: Archive generation and data export

### **Infrastructure**
- **Containerization**: Docker & Docker Compose
- **Database**: MongoDB with persistent volumes
- **Networking**: Internal Docker network
- **Storage**: Windows host volume mounting

## Data Flow

### 1. **RSS Feed Discovery & Creation**
```
News Websites → RSS-Bridge → Generated RSS Feeds → MongoDB URLs Collection
```

### 2. **Article Processing Pipeline**
```
RSS Feeds → Article URLs → Readability Service → Content Extraction → 
Readability Analysis → MongoDB Documents Collection
```

### 3. **Analytics & Export**
```
MongoDB Data → Web Dashboard (Charts/Reports) → CSV/JSON Export
MongoDB Data → Python API → ML Dataset Generation → Archive Download
```

## Key Features

### **Automated Processing**
- **Cron Scheduling**: Configurable intervals (default: daily at noon)
- **URL Management**: Database-driven RSS feed list
- **Error Handling**: Graceful failure recovery
- **Deduplication**: Prevents duplicate article processing

### **Readability Metrics**
- **Flesch Reading Ease**: 0-100 difficulty scale
- **Flesch-Kincaid Grade**: Educational grade level
- **SMOG Index**: Years of education needed
- **Dale-Chall**: Common word list based
- **Coleman-Liau**: Character-based calculation
- **Gunning Fog**: Complex word analysis
- **Spache**: Elementary education focus
- **Automated Readability**: Sentence/character ratio

### **Web Interface**
- **Daily Reports**: Aggregated metrics by date range
- **Trend Analysis**: Time-series visualization
- **Source Comparison**: Cross-publication analysis
- **Data Export**: CSV and JSON formats
- **Source Management**: Add/remove RSS feeds

### **Machine Learning Integration**
- **Dataset Generation**: Automated train/test split
- **Text Classification**: Reliability-based grouping
- **Archive Creation**: Compressed dataset download
- **External AI**: Text summarization API integration

## File Structure
```
Crawltest/
├── src/                          # Main Node.js application
│   ├── index.js                  # Main application entry point
│   ├── routeHandlers.js          # Express route handlers
│   ├── dbOperations.js           # Database abstraction layer
│   ├── readabilityAnalysis.js    # Analysis logic (refactored)
│   ├── views/                    # EJS templates
│   ├── package.json              # Node.js dependencies
│   └── .env                      # Environment configuration
├── rss-bridge/                   # RSS generation service
│   ├── bridges/                  # Custom bridge implementations
│   └── whitelist.txt            # Bridge security configuration
├── hug/                         # Python API component
│   ├── hug.py                   # Main Python API
│   ├── requirements.txt         # Python dependencies
│   └── Dockerfile              # Python container build
├── docs/                        # Project documentation
├── docker-compose.yml          # Service orchestration
├── Dockerfile                  # Main app container build
└── README.md                   # Basic project info
```

## Database Schema

### **documents** Collection
```javascript
{
  _id: ObjectId,
  url: "https://...",              // Article URL
  title: "Article Title",         // Article headline
  content: "...",                 // Extracted content
  "Host": "apnews.com",           // News source domain
  "publication_date": Date,        // When published
  "origin": "https://rss-url",    // RSS feed source
  
  // Text Statistics
  words: 500,
  sentences: 25,
  paragraphs: 8,
  characters: 2500,
  syllables: 750,
  
  // Readability Scores
  "Flesch": 65.2,
  "Flesch Kincaid": 8.5,
  "Smog": 9.1,
  "Dale Chall": 7.8,
  "Coleman Liau": 12.3,
  "Gunning Fog": 10.2,
  "Spache": 6.5,
  "Automated Readability": 9.8,
  
  date: Date                      // Processing timestamp
}
```

### **urls** Collection
```javascript
{
  _id: ObjectId,
  url: "https://rss-feed-url",    // RSS feed URL
  name: "AP Politics",            // Display name
  reliability: "high",            // Reliability classification
  bias: "center"                  // Political bias classification
}
```

## API Endpoints

### **Main Application (Port 4912)**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Single URL analysis |
| `/daily` | GET | Daily readability reports |
| `/graph` | GET | Trend visualization data |
| `/source/:origin` | GET | Individual source analysis |
| `/export` | GET | Data export (CSV/JSON) |
| `/add-url` | GET | Add RSS feed to monitoring |

### **Hug API (Port 30003)**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/generate_files` | GET | Create ML datasets |
| `/create_zip` | GET | Generate data archive |
| `/get_zip` | GET | Download data archive |
| `/export` | GET | Date-filtered export |
| `/wordcloud` | GET | Word frequency analysis |
| `/summarize` | POST | AI text summarization |

### **RSS-Bridge (Port 30002)**
| Bridge | URL | Purpose |
|--------|-----|---------|
| AP Politics | `/?action=display&bridge=APNewsPolitics&format=Atom` | AP Politics RSS |
| AP Top News | `/?action=display&bridge=APNewsTopNews&format=Atom` | AP General RSS |
| Reuters | `/?action=display&bridge=Reuters&format=Atom` | Reuters RSS |

## Configuration

### **Environment Variables**
- `INTERVAL`: Cron schedule for RSS crawling (default: `0 12 * * SUN-SAT`)

### **Database Volume**
- **Host Path**: `E:\NewsDatabase` (Windows)
- **Container Path**: `/data/db`
- **Purpose**: Persistent MongoDB storage

### **Network Ports**
- **4912**: Main web interface
- **30003**: Python API
- **30002**: RSS-Bridge interface
- **30001**: MongoDB (for debugging)

## Getting Started

### **Prerequisites**
- Docker Desktop (Windows)
- 4GB+ available RAM
- 10GB+ disk space for data storage

### **Quick Start**
```bash
# Clone repository
git clone <repository-url>
cd Crawltest

# Start all services
docker-compose up -d

# Access main interface
http://localhost:4912

# Add RSS feeds via web interface or API
curl "http://localhost:4912/add-url?url=https://rss-feed-url"

# View analytics
http://localhost:4912/daily
```

### **Development Mode**
```bash
# Start with hot reload
docker-compose up --watch

# View logs
docker-compose logs -f proxy-scanner
```

## Use Cases

### **News Organizations**
- Monitor article readability trends
- Compare readability across publications
- Track writing style changes over time

### **Researchers**
- Analyze media literacy requirements
- Study journalistic writing patterns
- Compare readability across topics/sources

### **Machine Learning**
- Train text classification models
- Develop readability prediction algorithms
- Create news quality assessment tools

### **Data Journalists**
- Generate readability reports
- Create publication comparisons
- Track news accessibility trends

## Future Enhancements

### **Planned Features**
- **Sentiment Analysis**: Emotional tone detection
- **Topic Classification**: Automatic categorization
- **Source Reliability**: ML-based reliability scoring
- **Real-time Processing**: WebSocket-based live updates
- **Advanced Visualization**: Interactive dashboard improvements

### **Technical Improvements**
- **Kubernetes Deployment**: Cloud-native orchestration
- **Redis Caching**: Performance optimization
- **Elasticsearch**: Advanced search capabilities
- **API Authentication**: Secure access control
- **Monitoring**: Comprehensive health checks
