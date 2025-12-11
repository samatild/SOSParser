# SOSParser - Docker Image
# Based on official Python slim image for better compatibility

FROM python:3.12-slim

# Build arguments
ARG VERSION=unknown
ARG BUILD_DATE
ARG VCS_REF

# Labels
LABEL org.opencontainers.image.title="SOSParser"
LABEL org.opencontainers.image.description="Linux sosreport/supportconfig analyzer"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.source="https://github.com/samatild/sosparser"
LABEL org.opencontainers.image.revision="${VCS_REF}"
LABEL maintainer="Samuel Matildes"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY VERSION ./VERSION
COPY src/ ./src/
COPY webapp/ ./webapp/

# Create necessary directories
RUN mkdir -p webapp/uploads webapp/outputs

# Set environment variables
ENV FLASK_APP=webapp/app.py
ENV PYTHONUNBUFFERED=1
ENV WEBAPP_HOST=0.0.0.0
ENV WEBAPP_PORT=8000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run the application with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "webapp.wsgi:application"]
