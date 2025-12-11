# Podman-compatible Dockerfile for StreamTV
# Same as Docker version, fully compatible with Podman

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

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
