# Quick Start Guide

## 🚀 Test the Python News Scanner Service

### Prerequisites
- Docker and Docker Compose installed

### Step 1: Build and Start All Services

```bash
# From the project root directory
docker-compose up --build -d

# Or start just the Python service (and its dependencies)
docker-compose up news-scanner -d
```

### Step 2: Verify Services are Running

```bash
# Check service status
docker-compose ps

# Check Python service logs specifically
docker-compose logs -f news-scanner
```

### Step 3: Access the Services

- **Python Service**: http://localhost:4913
- **Node.js Service**: http://localhost:4912
- **Python Health Check**: http://localhost:4913/health

### Step 4: Quick Functionality Test

1. **Add a Test RSS Source**:
   - Go to http://localhost:4913/sources
   - Add an RSS feed (e.g., `https://feeds.reuters.com/reuters/topNews`)
   - Watch the immediate scan in the logs

2. **Test Manual Scanning**:
   ```bash
   curl "http://localhost:4913/scan?url=https://www.reuters.com/world/"
   ```

3. **Check Health Status**:
   ```bash
   curl http://localhost:4913/health | jq
   ```

### Step 5: Compare with Node.js Service

- Add the same RSS source to both services
- Compare the readability analysis results
- Verify both services show similar article counts

### Troubleshooting

**If the service fails to start:**
```bash
# Check logs for errors
docker-compose logs news-scanner

# Common issues:
# 1. Port 4913 already in use - change port in docker-compose.yml
# 2. Database connection issues - ensure database service is running
# 3. Missing dependencies - rebuild the container: docker-compose build news-scanner
```

**Database Connection Issues:**
```bash
# Check all services status
docker-compose ps

# If database is not running, start it
docker-compose up readability-database -d
```

### Development Mode (Alternative)

If you prefer to run without Docker:

```bash
# Install Python dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env to use localhost instead of container names:
# MONGODB_URL=mongodb://localhost:27017
# READABILITY_SERVICE_URL=http://localhost:3000

# Run the service
python main.py
```

### Next Steps

Once verified working:
1. Test all major features (sources, daily reports, export)
2. Compare performance and accuracy with Node.js version
3. When satisfied, you can eventually replace the Node.js service
4. Update main docker-compose.yml to use the Python service instead

### Clean Up

To stop and remove the Python service:
```bash
# Stop just the Python service
docker-compose stop news-scanner

# Stop all services
docker-compose down

# Remove the Python service container
docker-compose rm news-scanner
```
