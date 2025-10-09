# ML Service - Optimized Docker Build

This ML service is optimized for fast Docker builds with comprehensive caching strategies to avoid re-downloading large Python packages.

## 🚀 Build Optimizations

### 1. Multi-Stage Build
- **Base stage**: Installs system dependencies and Python packages
- **Production stage**: Copies application code and sets up runtime
- Benefits: Smaller final image, better layer caching

### 2. Pip Cache Mount
- Uses Docker BuildKit cache mounts (`--mount=type=cache`)
- Caches pip downloads in `/root/.cache/pip`
- Persists between builds via host volume mount

### 3. Docker Layer Caching
- Requirements.txt copied before application code
- Dependencies installed in separate layer
- Only rebuilds when requirements change

### 4. BuildKit Inline Cache
- Enables cross-build cache sharing
- Improves cache hit rates across different machines

## 📁 Cache Directory Structure

```
ml-service/
├── .pip-cache/          # Host-side pip cache (mounted to container)
├── .dockerignore        # Optimized build context
├── Dockerfile           # Multi-stage optimized build
├── build.sh            # Linux/Mac build script
├── build.ps1           # Windows PowerShell build script
└── requirements.txt    # Python dependencies
```

## 🔧 Usage

### Quick Build (Recommended)
```bash
# Linux/Mac
./ml-service/build.sh

# Windows PowerShell
.\ml-service\build.ps1
```

### Docker Compose (Automatic)
```bash
docker-compose build ml-service
```

### Manual Build with BuildKit
```bash
export DOCKER_BUILDKIT=1
docker build --target production -t ml-service:latest ./ml-service/
```

## 📊 Performance Benefits

### First Build
- Downloads all packages (~1GB+)
- Creates cache layers
- Takes ~5-10 minutes

### Subsequent Builds
- Uses cached packages
- Only downloads new/changed dependencies
- Takes ~30-60 seconds

### Cache Persistence
- Pip cache persists in `./ml-service/.pip-cache/`
- Docker layers cached automatically
- Survives container restarts and rebuilds

## 🛠️ Troubleshooting

### Clear Cache
```bash
# Clear pip cache
rm -rf ml-service/.pip-cache/*

# Clear Docker build cache
docker builder prune
```

### Force Rebuild
```bash
docker-compose build --no-cache ml-service
```

### Check Cache Usage
```bash
# View pip cache contents
ls -la ml-service/.pip-cache/

# Check Docker build cache
docker system df
```

## 📦 Large Dependencies Cached

The following large packages are now cached and won't re-download:

- **PyTorch**: ~500MB (CUDA libraries)
- **Transformers**: ~200MB (tokenizers, safetensors)
- **Scikit-learn**: ~50MB (joblib, threadpoolctl)
- **OpenTelemetry**: ~100MB (various exporters)
- **NumPy/SciPy**: ~50MB (compiled binaries)

**Total cached size**: ~900MB+ of dependencies

## 🔄 Cache Sharing

The pip cache directory can be shared across:
- Different Docker builds
- Multiple developers
- CI/CD pipelines
- Different projects using similar dependencies

Simply copy the `.pip-cache/` directory to share cached packages.
