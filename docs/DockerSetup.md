# Docker Configuration Documentation

## Overview
The project uses Docker Compose to orchestrate a multi-service architecture for news article crawling, content analysis, and data storage. All services communicate through a shared Docker network.

## Architecture

### Service Topology
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   proxy-scanner │    │   readability    │    │  rss-bridge     │
│   (Main App)    │◄──►│   (Content       │    │  (RSS Gen)      │
│   Port: 30005   │    │   Extraction)    │    │  Port: 30002    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                                              │
         ▼                                              │
┌─────────────────┐    ┌──────────────────┐            │
│      hug        │    │ readability-     │◄───────────┘
│   (Python API) │◄──►│   database       │
│   Port: 30003   │    │   (MongoDB)      │
└─────────────────┘    │   Port: 30001    │
                       └──────────────────┘
```

## Services Configuration

### 1. **proxy-scanner** (Main Application)
```yaml
build:
  context: ./
develop:
  watch:
    - path: ./src
      action: sync
      target: /usr/src/app
      ignore:
        - node_modules/
networks:
  - readable
depends_on:
  - readability
  - readability-database
  - rss-bridge
ports:
  - "30005:8080"
volumes:
  - "./src:/usr/src/app"
restart: unless-stopped
```

**Features:**
- **Hot Reload**: File synchronization for development
- **Port Mapping**: External access via port 30005
- **Service Dependencies**: Waits for required services
- **Volume Mount**: Live code updates without rebuild

### 2. **readability** (Content Extraction)
```yaml
image: phpdockerio/readability-js-server
networks:
  - readable
expose:
  - "3000"
restart: unless-stopped
```

**Features:**
- **Pre-built Image**: Uses community readability service
- **Internal Network**: Only accessible within Docker network
- **Article Processing**: Extracts main content from web pages
- **Mozilla Readability**: Based on Firefox reader mode algorithm

### 3. **readability-database** (MongoDB)
```yaml
image: mongo
networks:
  - readable
environment:
  - PUID=1000
  - PGID=1000
volumes:
  - database:/data/db
ports:
  - 30001:27017
restart: unless-stopped
```

**Features:**
- **Official MongoDB**: Latest stable MongoDB image
- **User Permissions**: Configured for proper file ownership
- **Persistent Storage**: Named volume for data persistence
- **External Access**: Port 30001 for debugging/management

### 4. **rss-bridge** (RSS Feed Generation)
```yaml
image: rssbridge/rss-bridge:latest
networks:
  - readable
volumes:
  - ./rss-bridge/whitelist.txt:/app/whitelist.txt
  - ./rss-bridge/bridges:/app/bridges
ports:
  - 30002:80
restart: unless-stopped
```

**Features:**
- **Custom Bridges**: Mounted bridge implementations
- **Configuration**: Whitelist for security
- **Web Interface**: Accessible at port 30002
- **RSS Generation**: Creates feeds from websites without RSS

### 5. **hug** (Python Analytics API)
```yaml
build: ./hug/
command: hug -f hug.py
networks:
  - readable
depends_on:
  - readability-database
ports:
  - 30003:8000
volumes:
  - ./hug/.:/src
restart: unless-stopped
```

**Features:**
- **Custom Build**: Built from local Dockerfile
- **Python Environment**: Hug framework for API
- **Volume Mount**: Live code updates
- **Database Access**: Direct MongoDB connectivity

## Network Configuration

### Internal Network: `readable`
- **Type**: Bridge network
- **Purpose**: Isolates services while enabling communication
- **Security**: Prevents external access to internal services
- **Service Discovery**: Automatic hostname resolution between services

### Port Mappings
| Service | Internal Port | External Port | Purpose |
|---------|--------------|---------------|----------|
| proxy-scanner | 8080 | 30005 | Main web interface |
| readability | 3000 | - | Content extraction (internal) |
| readability-database | 27017 | 30001 | MongoDB access |
| rss-bridge | 80 | 30002 | RSS bridge interface |
| hug | 8000 | 30003 | Python API access |

## Volume Configuration

### Named Volumes
```yaml
volumes:
  database:
```
- **Purpose**: Persistent MongoDB data storage
- **Location**: Docker managed volume
- **Backup**: Requires Docker volume backup procedures

### Bind Mounts
| Service | Host Path | Container Path | Purpose |
|---------|-----------|----------------|----------|
| proxy-scanner | `./src` | `/usr/src/app` | Live code updates |
| rss-bridge | `./rss-bridge/whitelist.txt` | `/app/whitelist.txt` | Bridge configuration |
| rss-bridge | `./rss-bridge/bridges` | `/app/bridges` | Custom bridge code |
| hug | `./hug/.` | `/src` | Python code updates |

## Development Features

### Hot Reload Configuration
```yaml
develop:
  watch:
    - path: ./src
      action: sync
      target: /usr/src/app
      ignore:
        - node_modules/
```
- **File Watching**: Automatic detection of code changes
- **Sync Action**: Updates container files without restart
- **Ignored Paths**: Excludes node_modules for performance

### Environment Variables
- **PUID/PGID**: User/group ID mapping for file permissions
- **Custom Variables**: Defined in service `.env` files

## Startup Sequence

### Service Dependencies
1. **readability-database** (MongoDB) - Starts first
2. **readability** (Content service) - Independent startup
3. **rss-bridge** - Independent startup  
4. **hug** - Waits for database
5. **proxy-scanner** - Waits for all dependencies

### Health Checks
- **Restart Policy**: `unless-stopped` for all services
- **Automatic Recovery**: Services restart on failure
- **Dependency Handling**: Proper startup order with `depends_on`

## Build Configuration

### Main Application (Dockerfile)
```dockerfile
FROM node:14
WORKDIR /usr/src/app
ADD ./src/package.json /usr/src/app/package.json
RUN npm install
RUN npm install -g nodemon
EXPOSE 8080
CMD [ "npm", "start" ]
```

### Hug Component (hug/Dockerfile)
```dockerfile
FROM python:3.10.15-alpine3.20
ADD . /src
WORKDIR /src
RUN apk add --update nodejs=20.15.1-r0 npm
RUN npm install -g nodemon
ENV SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True
RUN pip install -r requirements.txt
```

## Management Commands

### Basic Operations
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f [service_name]

# Stop all services
docker-compose down

# Rebuild specific service
docker-compose build [service_name]

# Scale specific service
docker-compose up -d --scale [service_name]=2
```

### Development Commands
```bash
# Start with hot reload
docker-compose up --watch

# Build and start
docker-compose up --build

# Remove volumes (destructive)
docker-compose down -v
```

## Data Persistence

### Database Volume
- **Name**: `database`
- **Mount Point**: `/data/db`
- **Backup Strategy**: 
  ```bash
  docker run --rm -v crawltest_database:/data -v $(pwd):/backup alpine tar czf /backup/backup.tar.gz /data
  ```

### Configuration Persistence
- **Bridge Configs**: Version controlled in `./rss-bridge/`
- **Application Code**: Version controlled in `./src/`
- **Python Code**: Version controlled in `./hug/`

## Security Considerations

### Network Isolation
- Internal services not exposed to host network
- Only necessary ports exposed externally
- Bridge network prevents cross-container access

### File Permissions
- PUID/PGID mapping prevents permission issues
- Volume mounts use appropriate ownership
- Container user configurations

### Configuration Management
- Whitelist controls RSS bridge access
- Environment variables for sensitive configuration
- No hard-coded credentials in Docker configs

## Production Considerations

### Performance Optimization
- **Resource Limits**: Not currently set, should be configured
- **Health Checks**: Should be added for production
- **Load Balancing**: Can be added with multiple proxy-scanner instances

### Monitoring
- **Log Aggregation**: Consider centralized logging
- **Metrics Collection**: Add monitoring containers
- **Alerting**: Implement service health monitoring

### Backup Strategy
- **Database Backups**: Regular MongoDB dumps
- **Configuration Backups**: Version control for configs
- **Volume Snapshots**: Docker volume backup procedures
