# Podman-compatible Dockerfile for StreamTV
# Security-hardened with minimal attack surface
# Fully compatible with Podman

FROM python:3.12.7-slim@sha256:abc123def456789

# Security labels
LABEL maintainer="StreamTV Security Team"
LABEL security.scanning="enabled"
LABEL security.non-root="true"

# Set working directory
WORKDIR /app

# Install only essential runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /tmp/* /var/tmp/*

# Create non-root user
RUN useradd -m -u 1000 streamtv && \
    chown -R streamtv:streamtv /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY streamtv/ ./streamtv/
COPY schemas/ ./schemas/
COPY config.example.yaml .

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/schedules /app/logs && \
    chown -R streamtv:streamtv /app && \
    chmod -R 755 /app

# Security: Switch to non-root user
USER streamtv

# Expose port
EXPOSE 8410

# Security: Health check with timeout
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8410/api/health || exit 1

# Security: Use exec form to ensure proper signal handling
CMD ["python", "-m", "streamtv.main"]
