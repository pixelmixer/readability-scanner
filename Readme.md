# News Readability Analysis System

A comprehensive **multi-service news analysis system** that automatically crawls RSS feeds, analyzes article readability using multiple metrics, and provides web-based analytics with machine learning capabilities.

## 🚀 Quick Start

### Prerequisites
- Docker Desktop
- 4GB+ RAM available
- 10GB+ disk space at `E:\NewsDatabase`

### Start the System
```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# Access main interface
http://localhost:4912
```

## 🏗️ System Architecture

```
RSS Feeds → Content Extraction → Readability Analysis → MongoDB → Web Analytics
     ↓              ↓                    ↓               ↓           ↓
RSS-Bridge    Readability         Main App         Database    Dashboard
   :3939        Service            :4912           :27017      (Web UI)
                 :3000                 ↓
                                  Python API
                                    :3839
```

### Core Components
- **Main App** (`src/`): Node.js/Express - RSS crawling, readability analysis, web dashboard
- **Python API** (`hug/`): Hug framework - ML datasets, data export, advanced analytics  
- **RSS-Bridge** (`rss-bridge/`): PHP - Custom RSS generation for sites without feeds
- **MongoDB**: Database with persistent storage at `E:\NewsDatabase`

## 📊 Key Features

### 🔄 Automated Processing
- **Scheduled RSS crawling** with configurable cron intervals
- **8 readability metrics** calculated per article (Flesch, SMOG, Gunning Fog, etc.)
- **Content extraction** using Mozilla Readability algorithm
- **Duplicate prevention** with intelligent upsert patterns

### 📈 Analytics & Visualization
- **Web dashboard** with interactive charts and trend analysis
- **Date-range filtering** for historical data analysis
- **Source comparison** across different news publications
- **Export capabilities** (CSV, JSON formats)

### 🤖 Machine Learning Integration
- **Dataset generation** for training ML models
- **Text classification** by news source reliability
- **Archive creation** for downloadable research datasets
- **External AI integration** for text summarization

### 🌐 Custom RSS Generation
- **RSS-Bridge integration** for sites without native RSS feeds
- **Custom bridge development** for specific news sources
- **Caching strategies** for optimal performance

## 🔗 Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| **Main Interface** | http://localhost:4912 | Web dashboard, analytics, manual article processing |
| **Python API** | http://localhost:3839 | ML datasets, data export, advanced analytics |
| **RSS-Bridge** | http://localhost:3939 | Custom RSS feed generation interface |
| **MongoDB** | localhost:27017 | Direct database access (debugging) |

## 📚 Documentation

### Core Documentation
- **[Getting Started](GETTING_STARTED.md)** - Quick setup and usage guide
- **[Project Overview](docs/ProjectOverview.md)** - Complete system architecture
- **[Docker Setup](docs/DockerSetup.md)** - Container configuration and deployment

### Component Documentation
- **[Main Application](docs/MainApplication.md)** - Node.js crawler and analytics
- **[RSS-Bridge](docs/RSSBridge.md)** - Custom RSS feed generation
- **[Hug Component](docs/HugComponent.md)** - Python API and ML features

### Development Documentation
- **[Cursor Rules](docs/CursorRules.md)** - AI agent guidance system
- **[Quick Reference](docs/README.md)** - Developer fast access guide

## 🤖 AI Development Ready

This project includes a **world-class AI agent guidance system** using Cursor rules:

- **Automatic expertise activation** based on file patterns
- **Context-aware development guidance** for all technology stacks
- **Safety-first patterns** with embedded critical guidelines
- **Expert-level knowledge** for Node.js, Python, PHP, and Docker

AI coding agents can contribute at expert level immediately without additional setup.

## 🎯 Use Cases

### 📰 News Organizations
- Monitor article readability trends over time
- Compare readability across different publications
- Track writing style changes and accessibility

### 🔬 Researchers
- Analyze media literacy requirements across sources
- Study journalistic writing patterns and evolution
- Generate datasets for readability and bias analysis

### 🤖 Machine Learning
- Train text classification models on news content
- Develop readability prediction algorithms
- Create news quality assessment tools

### 📊 Data Journalists
- Generate automated readability reports
- Create publication comparison studies
- Track news accessibility trends

## 🛠️ Development

### Development Commands
```bash
# Start with hot reload
docker-compose up --watch

# View logs
docker-compose logs -f proxy-scanner

# Restart after changes
docker-compose restart [service-name]

# Stop all services
docker-compose down
```

### Adding News Sources
```bash
# Native RSS feed
curl "http://localhost:4912/add-url?url=https://feeds.reuters.com/reuters/topNews"

# Custom RSS via bridge
curl "http://localhost:4912/add-url?url=http://localhost:3939/?action=display&bridge=APNewsPolitics&format=Atom"
```

## 📈 Data & Analytics

### Database Collections
- **documents**: Articles with complete readability analysis
- **urls**: RSS feed sources with reliability classifications

### Readability Metrics
- Flesch Reading Ease, Flesch-Kincaid Grade Level
- SMOG Index, Dale-Chall Readability
- Coleman-Liau Index, Gunning Fog Index
- Spache Readability, Automated Readability Index

## 🔧 Configuration

### Environment Variables
```bash
# src/.env
INTERVAL=0 12 * * SUN-SAT  # Daily at noon (cron format)
```

### Database Volume
- **Host Path**: `E:\NewsDatabase` (Windows)
- **Container Path**: `/data/db`
- **Purpose**: Persistent MongoDB storage

## 🚨 Important Notes

- **Database Volume**: Never delete `E:\NewsDatabase` - contains all collected data
- **Testing**: Always test with single articles before batch processing
- **Performance**: Monitor Docker resource allocation for large datasets
- **Backup**: Regular database backups recommended for production use

## 📄 License

This project is licensed under the ISC License.

## 🤝 Contributing

1. Fork the repository
2. Review the [Cursor Rules](docs/CursorRules.md) for development guidance
3. Make your changes following established patterns
4. Test thoroughly using provided procedures
5. Submit a pull request

The AI guidance system ensures consistent, high-quality contributions across all technology stacks.