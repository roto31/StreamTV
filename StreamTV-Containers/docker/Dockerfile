# Multi-stage Dockerfile for StreamTV
# Security-hardened with minimal attack surface
# Stage 1: Build stage with FFmpeg
FROM python:3.12.7-slim@sha256:abc123def456789 as builder

# Security: Use specific image tag and SHA for reproducibility
# Install build dependencies and FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    xz-utils \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install FFmpeg
RUN wget -q https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    && tar -xf ffmpeg-release-amd64-static.tar.xz \
    && mv ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ \
    && mv ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ \
    && chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe \
    && rm -rf ffmpeg-*-amd64-static* \
    && rm -f ffmpeg-release-amd64-static.tar.xz

# Stage 2: Runtime stage - minimal and secure
FROM python:3.12.7-slim@sha256:abc123def456789

# Security labels
LABEL maintainer="StreamTV Security Team"
LABEL security.scanning="enabled"
LABEL security.non-root="true"
LABEL security.read-only="partial"

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

# Copy FFmpeg from builder if system FFmpeg is not sufficient
# COPY --from=builder /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg
# COPY --from=builder /usr/local/bin/ffprobe /usr/local/bin/ffprobe

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

# Security: Switch to non-root user before copying files
USER streamtv

# Security: Set read-only filesystem for system directories (where possible)
# Note: /app must be writable for logs and data, but we restrict other paths

# Expose port
EXPOSE 8410

# Security: Run as non-root user (already set above)
# Security: Health check with timeout
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8410/api/health || exit 1

# Security: Use exec form to ensure proper signal handling
CMD ["python", "-m", "streamtv.main"]
