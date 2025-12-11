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
   ```

2. **Run the container:**
   ```bash
   podman run -d \
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

### Using Pod (Kubernetes-style)

1. **Build the image:**
   ```bash
   podman build -t streamtv:latest .
   ```

2. **Create and start pod:**
   ```bash
   podman play kube pod.yaml
   ```

3. **Access the web interface:**
   Open http://localhost:8410

## Rootless Operation

Podman's main advantage is rootless operation:

```bash
# No sudo needed!
podman build -t streamtv:latest .
podman run -d --name streamtv -p 8410:8410 streamtv:latest
```

### Rootless Volume Storage

Rootless Podman stores volumes in:
- Linux: `~/.local/share/containers/storage/volumes/`
- macOS: `~/.local/share/containers/storage/volumes/`

## Configuration

### Environment Variables

Same as Docker - set via `-e` flag or in `podman-compose.yml`:

```bash
podman run -d \
  -e STREAMTV_YOUTUBE_API_KEY=your_key \
  -e STREAMTV_SERVER_BASE_URL=http://your-host:8410 \
  streamtv:latest
```

### Volume Mounts

```bash
# Named volumes (Podman-managed)
podman volume create streamtv_data
podman run -d -v streamtv_data:/app/data streamtv:latest

# Bind mounts (host directories)
podman run -d -v /host/path:/app/data:Z streamtv:latest
```

Note: Use `:Z` suffix for SELinux compatibility on Linux.

## Podman vs Docker Commands

| Docker | Podman |
|--------|--------|
| `docker build` | `podman build` |
| `docker run` | `podman run` |
| `docker ps` | `podman ps` |
| `docker logs` | `podman logs` |
| `docker-compose` | `podman-compose` |
| `docker volume` | `podman volume` |

## Advanced Usage

### Systemd Integration

Create a systemd service for auto-start:

```bash
# Generate systemd service file
podman generate systemd --name streamtv --files

# Install service
sudo cp container-streamtv.service /etc/systemd/system/
sudo systemctl enable container-streamtv.service
sudo systemctl start container-streamtv.service
```

### Pod Management

```bash
# Create pod
podman pod create --name streamtv-pod -p 8410:8410

# Add container to pod
podman run -d --pod streamtv-pod --name streamtv streamtv:latest

# List pods
podman pod ps

# Stop pod
podman pod stop streamtv-pod

# Remove pod
podman pod rm streamtv-pod
```

### Health Checks

Health checks work the same as Docker:

```bash
# Check health
podman healthcheck run streamtv

# Inspect health status
podman inspect streamtv | grep -A 10 Health
```

## Networking

### Rootless Networking

Rootless Podman uses slirp4netns for networking. Port forwarding works the same:

```bash
podman run -d -p 8410:8410 streamtv:latest
```

### Custom Networks

```bash
# Create network
podman network create streamtv-net

# Run container on network
podman run -d --network streamtv-net streamtv:latest
```

## Troubleshooting

### Permission Issues

If you encounter permission issues:

```bash
# Check Podman version
podman --version

# Check if running rootless
podman info | grep rootless

# Fix volume permissions (if needed)
podman unshare chown -R 1000:1000 /path/to/volume
```

### Port Conflicts

```bash
# Check what's using a port
sudo netstat -tulpn | grep 8410

# Or use ss
ss -tulpn | grep 8410
```

### View Logs

```bash
# Container logs
podman logs streamtv

# Follow logs
podman logs -f streamtv

# Last 100 lines
podman logs --tail 100 streamtv
```

### Container Shell Access

```bash
podman exec -it streamtv /bin/bash
```

## Migration from Docker

Podman is fully compatible with Docker:

1. **Build images the same way:**
   ```bash
   podman build -t streamtv:latest .
   ```

2. **Use same Dockerfiles:**
   - No changes needed to Dockerfile
   - Same syntax and commands

3. **Import Docker images:**
   ```bash
   # Save Docker image
   docker save streamtv:latest | podman load
   ```

4. **Use docker-compose files:**
   - Rename to `podman-compose.yml` or use `podman-compose` directly

## Production Deployment

### Systemd Service

```bash
# Generate service file
podman generate systemd --name streamtv --files --new

# Install
sudo cp container-streamtv.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable container-streamtv.service
sudo systemctl start container-streamtv.service
```

### Resource Limits

```bash
podman run -d \
  --memory=2g \
  --cpus=2 \
  --name streamtv \
  streamtv:latest
```

### Auto-restart

```bash
podman run -d \
  --restart=always \
  --name streamtv \
  streamtv:latest
```

## Security Features

1. **Rootless**: Run without root privileges
2. **User namespaces**: Better isolation
3. **SELinux**: Enhanced security on RHEL/Fedora
4. **Seccomp**: System call filtering
5. **Capabilities**: Fine-grained permissions

## See Also

- [Docker Distribution](../docker/README.md)
- [Docker Compose Distribution](../docker-compose/README.md)
- [Kubernetes Distribution](../kubernetes/README.md)
- [Podman Documentation](https://podman.io/docs/)
