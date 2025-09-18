# Dockerfile for RNA-Factory
# Multi-stage build for optimized production image

# Build stage
FROM python:3.9-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder stage
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY app/ ./app/
COPY models/ ./models/
COPY run.py .
COPY config.py .
COPY README.md .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

# Switch to non-root user
USER app

# Add local bin to PATH
ENV PATH=/root/.local/bin:$PATH

# Set DeepSeek API environment variables
ENV DEEPSEEK_API_KEY=sk-7a86aa9650be47c2ac08d877bc038216
ENV DEEPSEEK_API_BASE=https://api.deepseek.com
ENV DEEPSEEK_API_VERSION=v1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "--max-requests", "1000", "run:app"]
