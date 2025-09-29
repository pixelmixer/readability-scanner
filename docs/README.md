# News Readability Analysis System - Documentation

## Quick Links
- [Project Overview](ProjectOverview.md) - Complete system architecture and features
- [Main Application](MainApplication.md) - Node.js crawler and analytics
- [RSS-Bridge](RSSBridge.md) - RSS feed generation service  
- [Hug Component](HugComponent.md) - Python API for ML and data export
- [Docker Setup](DockerSetup.md) - Container orchestration and deployment

## Quick Start

### Prerequisites
- Docker Desktop (Windows)
- 4GB+ RAM available
- 10GB+ disk space at `E:\NewsDatabase`

### Start the System
```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f proxy-scanner
```

### Access Points
- **Main Interface**: http://localhost:4912
- **Python API**: http://localhost:3839  
- **RSS-Bridge**: http://localhost:3939
- **MongoDB**: localhost:27017

### Basic Usage
```bash
# Add RSS feed to monitor
curl "http://localhost:4912/add-url?url=https://rss-feed-url"

# View daily readability report
curl "http://localhost:4912/daily"

# Generate ML datasets
curl "http://localhost:3839/generate_files"

# Export data archive
curl -O "http://localhost:3839/get_zip"
```

## System Architecture

### Data Flow
```
RSS Feeds → Content Extraction → Readability Analysis → MongoDB → Web Analytics
     ↑              ↑                    ↑               ↑           ↑
RSS-Bridge    Readability         Main App         Database    Dashboard
   :3939        Service            :4912           :27017      (Web UI)
                 :3000                 ↓
                                  Python API
                                    :3839
```

### Key Components
- **Main App**: Scheduled RSS crawling and readability analysis
- **RSS-Bridge**: Generates RSS feeds for sites without them
- **MongoDB**: Persistent storage with Windows volume at `E:\NewsDatabase`
- **Python API**: ML dataset generation and advanced analytics
- **Web Dashboard**: Interactive reports and visualizations

## Configuration

### Environment Variables
```bash
# src/.env
INTERVAL=0 12 * * SUN-SAT  # Daily at noon
```

### Database Location
- **Host Path**: `E:\NewsDatabase`
- **Purpose**: Persistent MongoDB storage on Windows

### Network Ports
| Service | Port | Purpose |
|---------|------|---------|
| Main App | 4912 | Web interface |
| Python API | 3839 | ML and export API |
| RSS-Bridge | 3939 | RSS generation |
| MongoDB | 27017 | Database (debugging) |

## Development

### Hot Reload
```bash
# Start with file watching
docker-compose up --watch
```

### Service Management
```bash
# Restart specific service
docker-compose restart proxy-scanner

# View service logs
docker-compose logs -f [service-name]

# Rebuild after code changes
docker-compose build proxy-scanner
```

## Troubleshooting

### Common Issues
1. **Port conflicts**: Ensure ports 4912, 3839, 3939, 27017 are available
2. **Volume permissions**: Ensure `E:\NewsDatabase` directory exists and is writable
3. **Memory issues**: Ensure Docker has sufficient RAM allocation
4. **Network issues**: Check Docker network configuration

### Health Checks
```bash
# Test main application
curl http://localhost:4912

# Test Python API
curl http://localhost:3839/happy_birthday?name=Test

# Test RSS-Bridge
curl http://localhost:3939

# Test MongoDB connection
docker exec -it crawltest_readability-database_1 mongosh
```

### Log Locations
```bash
# Application logs
docker-compose logs proxy-scanner

# Database logs
docker-compose logs readability-database

# Python API logs
docker-compose logs hug
```

## Data Management

### Backup Database
```bash
# Create backup
docker exec crawltest_readability-database_1 mongodump --out /backup
docker cp crawltest_readability-database_1:/backup ./backup

# Restore backup
docker exec crawltest_readability-database_1 mongorestore /backup
```

### Export Data
- **Web Interface**: http://localhost:4912/export
- **Python API**: http://localhost:3839/create_zip
- **Direct MongoDB**: Use MongoDB Compass or mongosh

## Next Steps
After documentation and startup, the system is ready for:
1. Adding RSS feeds for monitoring
2. Configuring cron schedule as needed  
3. Setting up regular data backups
4. Customizing readability metrics or analysis
5. Extending with additional news sources
