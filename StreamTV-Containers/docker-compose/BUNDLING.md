# Dependency Bundling for Containers

## Overview

StreamTV container builds (Docker, Podman, Kubernetes) **do not use bundled dependencies**. Instead, they rely on system packages installed during the container build process.

## Why No Bundling?

1. **Container Isolation**: Containers already provide isolation, so bundling dependencies is unnecessary
2. **Size Optimization**: System packages are more efficient in containers
3. **Security Updates**: System packages can be updated via package managers
4. **Proven Approach**: Current Dockerfile approach is working correctly

## Current Implementation

### Dockerfile Approach

The Dockerfile installs dependencies using system package managers:

```dockerfile
# Python is provided by base image (python:3.12-slim)
FROM python:3.12-slim

# FFmpeg is installed via apt-get
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*
```

### Benefits

- **Smaller Images**: System packages are optimized for containers
- **Security**: Regular security updates via package managers
- **Compatibility**: Works across all container platforms
- **Maintainability**: Standard approach, easy to update

## Platform-Specific Notes

### Docker
- Uses `python:3.12-slim` base image
- Installs FFmpeg via `apt-get`
- No bundling required

### Podman
- Same approach as Docker
- Compatible with Dockerfile

### Kubernetes
- Uses same container images
- No special bundling needed

## Future Considerations

If bundling becomes necessary for containers:

1. **Static Builds**: Use static FFmpeg builds for smaller images
2. **Python Embeddable**: Use Python embeddable distribution
3. **Multi-stage Builds**: Separate build and runtime stages

However, the current system package approach is recommended and will continue to be used.

## Related Documentation

- [Dockerfile](../docker-compose/Dockerfile)
- [docker-compose.yml](../docker-compose/docker-compose.yml)
- [BUNDLING_DEPENDENCIES.md](../../docs/BUNDLING_DEPENDENCIES.md)

