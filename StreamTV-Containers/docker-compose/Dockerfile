# Multi-stage Dockerfile for StreamTV
# Stage 1: Build stage with FFmpeg
FROM python:3.12-slim as builder

# Install build dependencies and FFmpeg
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Install FFmpeg
RUN wget -q https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    && tar -xf ffmpeg-release-amd64-static.tar.xz \
    && mv ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ \
    && mv ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ \
    && chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe \
    && rm -rf ffmpeg-*-amd64-static*

# Stage 2: Runtime stage
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

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

# Create necessary directories
RUN mkdir -p /app/data /app/schedules /app/logs && \
    chown -R streamtv:streamtv /app

# Switch to non-root user
USER streamtv

# Expose port
EXPOSE 8410

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8410/api/health || exit 1

# Default command
CMD ["python", "-m", "streamtv.main"]
