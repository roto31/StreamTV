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
