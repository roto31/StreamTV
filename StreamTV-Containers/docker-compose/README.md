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
```

### Resource Limits

```yaml
services:
  streamtv:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Logging Configuration

```yaml
services:
  streamtv:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        compress: "true"
```

## Monitoring

### Health Checks

All services include health checks:

```bash
# Check health status
docker-compose ps

# View health check logs
docker-compose exec streamtv curl http://localhost:8410/api/health
```

### Log Aggregation

Use Docker logging drivers or external tools:

```yaml
services:
  streamtv:
    logging:
      driver: "fluentd"
      options:
        fluentd-address: "localhost:24224"
        tag: "streamtv"
```

## Backup and Restore

### Backup Script

Create `backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="./backups"
mkdir -p $BACKUP_DIR

# Backup volumes
docker run --rm \
  -v streamtv_data:/data \
  -v $(pwd)/$BACKUP_DIR:/backup \
  alpine tar czf /backup/streamtv_data_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .
```

### Restore Script

Create `restore.sh`:

```bash
#!/bin/bash
BACKUP_FILE=$1

docker run --rm \
  -v streamtv_data:/data \
  -v $(pwd)/backups:/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/$BACKUP_FILE -C /data"
```

## Scaling

### Horizontal Scaling (with load balancer)

```yaml
services:
  streamtv:
    deploy:
      replicas: 3
```

Note: StreamTV uses SQLite by default. For multiple replicas, use PostgreSQL or another shared database.

## Environment-Specific Configs

### Development

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Staging

```bash
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up
```

### Production

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Troubleshooting

### View All Logs

```bash
docker-compose logs
```

### Restart Services

```bash
docker-compose restart
```

### Rebuild After Changes

```bash
docker-compose build --no-cache
docker-compose up -d
```

### Clean Up

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

## Best Practices

1. **Use named volumes** for persistent data
2. **Set resource limits** to prevent resource exhaustion
3. **Enable health checks** for automatic recovery
4. **Use secrets** for sensitive configuration
5. **Regular backups** of volume data
6. **Monitor logs** for issues
7. **Keep images updated** for security patches

## See Also

- [Docker Documentation](../docker/README.md)
- [Kubernetes Distribution](../kubernetes/README.md)
- [Podman Distribution](../podman/README.md)
