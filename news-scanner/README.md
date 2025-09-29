# News Scanner Python Service

A modern Python-based replacement for the Node.js news readability analysis system. Built with FastAPI, this service provides RSS feed scanning, content extraction, readability analysis, and web reporting.

## 🚀 Features

- **FastAPI Web Framework**: Modern, fast, and async-capable
- **Modular Architecture**: Clean separation of concerns with dedicated modules
- **RSS Feed Scanning**: Automated scanning with configurable cron schedules  
- **Readability Analysis**: Complete implementation of all readability formulas
- **MongoDB Integration**: Async database operations with proper indexing
- **Web Interface**: Jinja2 templates with Bootstrap UI
- **Docker Support**: Full containerization with health checks
- **Concurrent Processing**: Async/await with controlled concurrency
- **Error Handling**: Comprehensive error tracking and reporting
- **User Agent Rotation**: Bot detection avoidance
- **Retry Logic**: Robust error recovery with exponential backoff

## 🏗️ Architecture

```
news-scanner/
├── api/                 # FastAPI routes and application
│   ├── routes/         # Route modules (sources, daily, etc.)
│   ├── app.py          # Main FastAPI application
│   └── dependencies.py # Shared dependencies
├── database/           # MongoDB operations
│   ├── articles.py     # Article repository
│   ├── sources.py      # Source repository  
│   └── connection.py   # Database connection manager
├── models/             # Pydantic data models
├── readability/        # Readability analysis engine
│   ├── analyzer.py     # Main analyzer
│   ├── formulas.py     # Readability formulas
│   └── text_stats.py   # Text statistics
├── scanner/            # RSS scanning and content extraction
│   ├── rss_parser.py   # RSS feed parsing
│   ├── content_extractor.py # Content extraction via readability service
│   ├── scanner.py      # Main scanning orchestrator
│   └── user_agents.py  # User agent rotation
├── scheduler/          # Cron job scheduling
├── templates/          # Jinja2 templates
│   ├── layouts/        # Base templates
│   ├── pages/          # Page templates
│   └── partials/       # Reusable components
├── utils/              # Utility functions
├── config.py           # Configuration management
├── main.py             # Application entry point
└── requirements.txt    # Python dependencies
```

## 🐳 Docker Setup

### Running with the Main Docker Compose

The Python service is now integrated into the main `docker-compose.yml` file and runs alongside all other services:

```bash
# Build and run all services including the new Python service
docker-compose up --build

# Or run specific services
docker-compose up news-scanner

# View logs
docker-compose logs -f news-scanner
```

**Access the services**:
- **Python Service**: http://localhost:4913
- **Node.js Service**: http://localhost:4912 
- **Health Check**: http://localhost:4913/health

### Development Mode

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run the service
python main.py
```

## 🔧 Configuration

Configuration is managed through environment variables and the `config.py` file:

```python
# Key settings
SCAN_INTERVAL=0 */6 * * *      # Cron expression for scanning
MAX_CONCURRENT_SCANS=5          # Concurrent RSS scans
REQUEST_DELAY_MS=100            # Delay between requests
MONGODB_URL=mongodb://localhost:27017
READABILITY_SERVICE_URL=http://readability:3000
```

## 📊 API Endpoints

### Web Interface
- `GET /` - Redirects to sources page
- `GET /sources` - Source management interface
- `GET /daily` - Daily readability reports
- `GET /graph` - Graph visualization (coming soon)

### API Endpoints
- `GET /health` - Service health check
- `GET /sources/api` - Get sources as JSON
- `POST /sources/add` - Add new RSS source
- `POST /sources/refresh/{id}` - Manual source refresh
- `GET /scan?url=<url>` - Manual article scanning
- `GET /export?type=csv` - Export data

## 🔍 Readability Formulas

The service implements all major readability formulas:

- **Flesch Reading Ease**: General readability score (0-100)
- **Flesch-Kincaid Grade**: U.S. grade level equivalent
- **SMOG Index**: Years of education needed
- **Dale-Chall**: Difficulty based on word familiarity
- **Coleman-Liau**: Based on character and sentence counts
- **Gunning Fog**: Complex word percentage
- **Spache**: For primary reading levels
- **Automated Readability Index (ARI)**: Character-based formula

## 🎯 Migration Status

This Python service replicates all functionality from the original Node.js version:

✅ **Completed**:
- RSS feed parsing and validation
- Content extraction via readability service
- All readability formula calculations
- MongoDB database operations (articles & sources)
- Web interface with Bootstrap UI
- Source management (add, edit, delete, refresh)
- Automated scheduling with cron expressions
- Export functionality (CSV/JSON)
- Health monitoring and logging
- Docker containerization
- User agent rotation and retry logic

🚧 **In Progress**:
- Graph visualization features
- Advanced filtering and search
- Performance optimizations

## 🧪 Testing

### Manual Testing

1. **Health Check**:
   ```bash
   curl http://localhost:4913/health
   ```

2. **Scan Single Article**:
   ```bash
   curl "http://localhost:4913/scan?url=https://example.com/article"
   ```

3. **Add RSS Source** (via web interface):
   - Navigate to http://localhost:4913/sources
   - Add an RSS feed URL
   - Monitor the immediate scan results

### Validation

- Compare readability scores between Node.js and Python versions
- Verify identical database storage format
- Test concurrent scanning performance
- Validate cron scheduling behavior

## 🚦 Monitoring

### Logs
```bash
# View application logs
docker-compose -f docker-compose-python.yml logs -f news-scanner-python

# View specific modules
grep "RSS Scheduler" news-scanner.log
grep "readability analysis" news-scanner.log
```

### Health Monitoring
The `/health` endpoint provides comprehensive status:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "database": "connected",
  "scheduler": {
    "running": true,
    "schedule": "0 */6 * * *",
    "schedule_human": "Every 6 hours",
    "next_run": "2024-01-01T18:00:00"
  }
}
```

## 🔄 Migration Plan

1. **Phase 1**: Run both services in parallel ✅
2. **Phase 2**: Validate functionality parity
3. **Phase 3**: Performance comparison
4. **Phase 4**: Switch traffic to Python service
5. **Phase 5**: Decommission Node.js service

## 🤝 Contributing

This service is designed to be drop-in compatible with the existing system while providing improved maintainability and performance.

## 📝 License

Same as the original project.
