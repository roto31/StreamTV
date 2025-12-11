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
PLEX_BASE_URL=http://192.168.1.100:32400
PLEX_TOKEN=your_plex_token
```

### Mounting Custom Config

To use a custom `config.yaml`:

```yaml
volumes:
  - ./config.yaml:/app/config.yaml:ro
```

## Volumes

The Docker Compose setup creates three named volumes:

- **streamtv_data**: Database and persistent application data
- **streamtv_schedules**: Schedule YAML files
- **streamtv_logs**: Application logs

### Accessing Volumes

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect streamtv_data

# Backup data
docker run --rm -v streamtv_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/streamtv_data_backup.tar.gz -C /data .

# Restore data
docker run --rm -v streamtv_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/streamtv_data_backup.tar.gz -C /data
```

## Production Deployment

### Using Production Override

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

This applies:
- Resource limits
- Log rotation
- Production logging levels
- Optimized restart policies

### Building for Production

```bash
# Build with specific tag
docker build -t streamtv:v1.0.0 .

# Tag for registry
docker tag streamtv:v1.0.0 your-registry/streamtv:v1.0.0

# Push to registry
docker push your-registry/streamtv:v1.0.0
```

### Health Checks

The container includes health checks. Monitor with:

```bash
# Check health status
docker ps  # Shows health status

# Inspect health check
docker inspect streamtv | grep -A 10 Health
```

## Networking

### Ports

- **8410**: Main web interface and API
- **5004**: HDHomeRun streaming (if enabled)
- **1900/udp**: SSDP discovery (optional)

### Custom Network

The Docker Compose setup creates a bridge network. To connect other containers:

```yaml
services:
  other-service:
    networks:
      - streamtv-network
```

## Troubleshooting

### View Logs

```bash
# All logs
docker-compose logs streamtv

# Follow logs
docker-compose logs -f streamtv

# Last 100 lines
docker-compose logs --tail=100 streamtv
```

### Container Shell Access

```bash
docker exec -it streamtv /bin/bash
```

### Check Container Status

```bash
docker ps -a | grep streamtv
docker inspect streamtv
```

### Restart Container

```bash
docker-compose restart streamtv
```

### Rebuild After Changes

```bash
docker-compose build --no-cache streamtv
docker-compose up -d streamtv
```

## Updating

1. **Pull latest code/changes**

2. **Rebuild:**
   ```bash
   docker-compose build streamtv
   docker-compose up -d streamtv
   ```

3. **Or with no cache:**
   ```bash
   docker-compose build --no-cache streamtv
   docker-compose up -d streamtv
   ```

## Security Considerations

1. **Non-root user**: Container runs as user `streamtv` (UID 1000)
2. **Read-only config**: Mount config files as read-only when possible
3. **Secrets**: Use Docker secrets or environment files for sensitive data
4. **Network**: Use custom networks to isolate containers
5. **Updates**: Regularly update base images and dependencies

## Resource Requirements

### Minimum
- CPU: 0.5 cores
- Memory: 512MB
- Disk: 1GB

### Recommended
- CPU: 1-2 cores
- Memory: 1-2GB
- Disk: 5GB+ (for database and logs)

## Integration with Plex

1. **Start StreamTV container**

2. **In Plex Settings → Live TV & DVR:**
   - Add Tuner: `http://YOUR_HOST_IP:8410/hdhomerun/discover.json`
   - Add Guide: `http://YOUR_HOST_IP:8410/iptv/xmltv.xml`

3. **Map channels and start watching**

## Support

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- See `docs/` directory for StreamTV documentation

## License

See LICENSE file for details.
