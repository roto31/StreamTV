# Containers

Complete documentation for StreamTV container distributions.

# StreamTV Container Distributions

Complete container distributions for StreamTV across all major container platforms.

## Available Distributions

### 🐳 [Docker](docker/)
- Single container deployment
- Multi-stage builds
- Health checks
- Production-ready configuration

### 🐙 [Docker Compose](docker-compose/)
- Multi-service orchestration
- Volume management
- Network isolation
- Production overrides

### ☸️ [Kubernetes](kubernetes/)
- Complete K8s manifests
- ConfigMaps and Secrets
- PersistentVolumeClaims
- Ingress configuration
- Kustomize support

### 🔷 [Podman](podman/)
- Rootless containers
- Docker-compatible
- Pod support
- Systemd integration

## Quick Comparison

| Feature | Docker | Docker Compose | Kubernetes | Podman |
|---------|--------|----------------|------------|--------|
| **Ease of Use** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| **Orchestration** | ❌ | ✅ | ✅✅ | ✅ |
| **Production Ready** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Rootless** | ❌ | ❌ | ✅ | ✅ |
| **Scaling** | Manual | Limited | ✅✅ | Limited |
| **Best For** | Development | Small deployments | Production clusters | Rootless needs |

## Choosing the Right Platform

### Use Docker if:
- You're getting started
- Single server deployment
- Simple setup needed
- Development environment

### Use Docker Compose if:
- Multiple services needed
- Local development
- Small production deployments
- Easy orchestration

### Use Kubernetes if:
- Production cluster deployment
- Need auto-scaling
- High availability required
- Enterprise environment

### Use Podman if:
- Rootless operation needed
- Security is priority
- Docker alternative desired
- Systemd integration needed

## Common Tasks

### Building Images

**Docker/Podman:**
```bash
docker build -t streamtv:latest .
podman build -t streamtv:latest .
```

**Docker Compose:**
```bash
docker-compose build
```

**Kubernetes:**
```bash
# Build and push to registry
docker build -t registry/streamtv:v1.0.0 .
docker push registry/streamtv:v1.0.0
```

### Running Containers

**Docker:**
```bash
docker run -d -p 8410:8410 streamtv:latest
```

**Docker Compose:**
```bash
docker-compose up -d
```

**Kubernetes:**
```bash
kubectl apply -f deployment.yaml
```

**Podman:**
```bash
podman run -d -p 8410:8410 streamtv:latest
```

### Viewing Logs

**Docker/Podman:**
```bash
docker logs -f streamtv
podman logs -f streamtv
```

**Docker Compose:**
```bash
docker-compose logs -f
```

**Kubernetes:**
```bash
kubectl logs -f deployment/streamtv
```

## Configuration

All platforms support the same environment variables:

```bash
STREAMTV_SERVER_HOST=0.0.0.0
STREAMTV_SERVER_PORT=8410
STREAMTV_YOUTUBE_API_KEY=your_key
STREAMTV_ARCHIVE_ORG_USERNAME=username
STREAMTV_ARCHIVE_ORG_PASSWORD=password
```

See individual platform READMEs for platform-specific configuration.

## Volumes and Persistence

All platforms support persistent storage:

- **Docker**: Named volumes or bind mounts
- **Docker Compose**: Named volumes
- **Kubernetes**: PersistentVolumeClaims
- **Podman**: Named volumes or bind mounts

## Networking

### Ports

- **8410**: Main web interface and API
- **5004**: HDHomeRun streaming
- **1900/udp**: SSDP discovery

### Access Methods

- **Docker/Podman**: Direct port mapping
- **Docker Compose**: Service networking
- **Kubernetes**: Service, Ingress, or LoadBalancer

## Health Checks

All platforms include health checks:

- HTTP endpoint: `/api/health`
- Interval: 30 seconds
- Timeout: 10 seconds
- Retries: 3

## Migration Between Platforms

### Docker → Docker Compose

1. Use existing Dockerfile
2. Create `docker-compose.yml`
3. Run `docker-compose up`

### Docker → Kubernetes

1. Build and push image to registry
2. Update `deployment.yaml` with image
3. Apply manifests: `kubectl apply -f .`

### Docker → Podman

1. Use same Dockerfile
2. Replace `docker` with `podman` in commands
3. No other changes needed!

## Best Practices

1. **Use .env files** for sensitive configuration
2. **Enable health checks** for automatic recovery
3. **Set resource limits** to prevent resource exhaustion
4. **Use named volumes** for persistent data
5. **Regular backups** of volume data
6. **Keep images updated** for security patches
7. **Monitor logs** for issues
8. **Use secrets management** for production

## Troubleshooting

### Common Issues

**Port already in use:**
- Change port in configuration
- Or stop conflicting service

**Permission denied:**
- Check volume permissions
- Use rootless Podman if possible

**Container won't start:**
- Check logs: `docker logs streamtv`
- Verify environment variables
- Check health endpoint

**Data not persisting:**
- Verify volume mounts
- Check volume permissions
- Ensure volumes are created

## Support

- [Docker Documentation](docker/README.md)
- [Docker Compose Documentation](docker-compose/README.md)
- [Kubernetes Documentation](kubernetes/README.md)
- [Podman Documentation](podman/README.md)

## License

See LICENSE file for details.

---

## Docker

# StreamTV Docker Distribution

Complete Docker distribution for StreamTV with multi-stage builds, health checks, and production-ready configurations.

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone or extract this directory**

2. **Create environment file (optional):**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start StreamTV:**
   ```bash
   docker-compose up -d
   ```

4. **Access the web interface:**
   Open http://localhost:8410 in your browser

5. **View logs:**
   ```bash
   docker-compose logs -f streamtv
   ```

6. **Stop StreamTV:**
   ```bash
   docker-compose down
   ```

### Using Docker Directly

1. **Build the image:**
   ```bash
   docker build -t streamtv:latest .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     --name streamtv \
     -p 8410:8410 \
     -v streamtv_data:/app/data \
     -v streamtv_schedules:/app/schedules \
     -v streamtv_logs:/app/logs \
     -e STREAMTV_SERVER_BASE_URL=http://localhost:8410 \
     streamtv:latest
   ```

3. **Access the web interface:**
   Open http://localhost:8410

## Configuration

### Environment Variables

All configuration can be set via environment variables:

```bash
# Server
STREAMTV_SERVER_HOST=0.0.0.0
STREAMTV_SERVER_PORT=8410
STREAMTV_SERVER_BASE_URL=http://localhost:8410

# Database
STREAMTV_DATABASE_URL=sqlite:///./data/streamtv.db

# YouTube
STREAMTV_YOUTUBE_ENABLED=true
STREAMTV_YOUTUBE_API_KEY=your_api_key_here

# Archive.org
STREAMTV_ARCHIVE_ORG_ENABLED=true
STREAMTV_ARCHIVE_ORG_USERNAME=your_username
STREAMTV_ARCHIVE_ORG_PASSWORD=your_password

# Security
STREAMTV_SECURITY_ACCESS_TOKEN=your_token_here
```

### Using .env File

Create a `.env` file in the same directory as `docker-compose.yml`:

```env
YOUTUBE_API_KEY=your_key_here
ARCHIVE_ORG_USERNAME=your_username
ARCHIVE_ORG_PASSWORD=your_password
PLEX_BASE_URL=http://:32400
PLEX_TOKEN=your_plex_token
```

### Mounting Custom Config

To use a custom `config.yaml`:


---

## Docker Compose

# StreamTV Docker Compose Distribution

Enhanced Docker Compose distribution with additional services, monitoring, and production configurations.

## Features

- **Multi-service orchestration**: StreamTV with optional supporting services
- **Health monitoring**: Built-in health checks and monitoring
- **Volume management**: Persistent data storage
- **Network isolation**: Custom networks for service communication
- **Production ready**: Optimized configurations for production use

## Quick Start

### Basic Setup

```bash
docker-compose up -d
```

### With Production Override

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Services

### streamtv (Main Service)

The core StreamTV application.

**Ports:**
- 8410: Web interface and API
- 5004: HDHomeRun streaming
- 1900/udp: SSDP discovery

### Optional Services

Add these to `docker-compose.yml` as needed:

#### Redis (for caching)

```yaml
services:
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    networks:
      - streamtv-network
```

#### PostgreSQL (alternative database)

```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: streamtv
      POSTGRES_USER: streamtv
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - streamtv-network
```

## Advanced Configuration

### Custom Networks

```yaml
networks:
  streamtv-frontend:
    driver: bridge
  streamtv-backend:
    driver: bridge
    internal: true  # Isolated network

---

## Kubernetes

# StreamTV Kubernetes Distribution

Complete Kubernetes manifests for deploying StreamTV in a Kubernetes cluster.

## Prerequisites

- Kubernetes cluster (v1.20+)
- kubectl configured
- PersistentVolume provisioner (for data storage)
- Ingress controller (optional, for external access)

## Quick Start

### 1. Create Namespace

```bash
kubectl apply -f namespace.yaml
```

### 2. Create ConfigMap and Secrets

```bash
# Update configmap.yaml with your settings
kubectl apply -f configmap.yaml

# Create secrets (update with your values)
kubectl apply -f secrets.yaml
# Or create from command line:
kubectl create secret generic streamtv-secrets \
  --from-literal=youtube-api-key='your-key' \
  --from-literal=access-token='your-token' \
  -n streamtv
```

### 3. Create PersistentVolumeClaims

```bash
kubectl apply -f pvc.yaml
```

### 4. Deploy StreamTV

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

### 5. (Optional) Create Ingress

```bash
# Update ingress.yaml with your domain
kubectl apply -f ingress.yaml
```

### 6. Check Status

```bash
kubectl get pods -n streamtv
kubectl get svc -n streamtv
kubectl logs -f deployment/streamtv -n streamtv
```

## Using Kustomize

```bash
# Apply all resources
kubectl apply -k .

# With custom image
kubectl apply -k . --dry-run=client -o yaml | \
  sed 's|streamtv:latest|your-registry/streamtv:v1.0.0|' | \
  kubectl apply -f -
```

## Configuration

### ConfigMap

Update `configmap.yaml` with your settings:

```yaml
data:
  base_url: "http://streamtv.example.com"
  plex-base-url: "http://plex.example.com:32400"
```

### Secrets

Create secrets for sensitive data:

```bash
kubectl create secret generic streamtv-secrets \
  --from-literal=youtube-api-key='your-key' \
  --from-literal=archive-org-username='username' \
  --from-literal=archive-org-password='password' \
  --from-literal=access-token='token' \
  --from-literal=plex-token='plex-token' \
  -n streamtv
```


---

## Podman

# StreamTV Podman Distribution

Complete Podman distribution for StreamTV. Podman is a daemonless container engine that is fully compatible with Docker images and commands.

## Why Podman?

- **Rootless**: Run containers without root privileges
- **Daemonless**: No background daemon required
- **Docker-compatible**: Uses same images and commands
- **Security**: Better isolation and security features
- **Kubernetes**: Native Kubernetes support via `podman play kube`

## Prerequisites

Install Podman on your system:

### Linux

```bash
# Ubuntu/Debian
sudo apt install podman

# Fedora/RHEL/CentOS
sudo dnf install podman

# Arch Linux
sudo pacman -S podman
```

### macOS

```bash
brew install podman
podman machine init
podman machine start
```

### Windows

```powershell
# Using Chocolatey
choco install podman

# Or download from podman.io
```

## Quick Start

### Using Podman Compose

1. **Install podman-compose:**
   ```bash
   pip install podman-compose
   # Or
   sudo dnf install podman-compose
   ```

2. **Start StreamTV:**
   ```bash
   podman-compose up -d
   ```

3. **Access the web interface:**
   Open http://localhost:8410

4. **View logs:**
   ```bash
   podman-compose logs -f streamtv
   ```

5. **Stop StreamTV:**
   ```bash
   podman-compose down
   ```

### Using Podman Directly

1. **Build the image:**
   ```bash
   podman build -t streamtv:latest .


## Common Documentation

### API Documentation
# StreamTV API Documentation

This document describes the RESTful API for StreamTV, modeled after ErsatzTV's API structure.

## Base URL

All API endpoints are prefixed with `/api` unless otherwise noted.

## Authentication

If `api_key_required` is enabled in configuration, include the access token as a query parameter:
```
?access_token=YOUR_TOKEN
```

## Endpoints

### Channels

#### Get All Channels
```
GET /api/channels
```

Returns a list of all channels.

**Response:**
```json
[
  {
    "id": 1,
    "number": "1",
    "name": "My Channel",
    "group": "Entertainment",
    "enabled": true,
    "logo_path": null,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

#### Get Channel by ID
```
GET /api/channels/{channel_id}
```

#### Get Channel by Number
```
GET /api/channels/number/{channel_number}
```

#### Create Channel
```
POST /api/channels
Content-Type: application/json

{
  "number": "1",
  "name": "My Channel",

