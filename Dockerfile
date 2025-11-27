# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

# Add metadata
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

LABEL org.opencontainers.image.created=$BUILD_DATE \
      org.opencontainers.image.revision=$VCS_REF \
      org.opencontainers.image.version=$VERSION \
      org.opencontainers.image.title="AgendaFlow" \
      org.opencontainers.image.description="RAG service for Paris events" \
      org.opencontainers.image.source="https://github.com/Septimus4/AgendaFlow"

# Create non-root user
RUN groupadd -r agendaflow && useradd -r -g agendaflow agendaflow

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/agendaflow/.local

# Copy application code
COPY --chown=agendaflow:agendaflow . .

# Create data directories
RUN mkdir -p data/raw data/clean data/index/faiss data/artifacts data/embeddings_cache && \
    chown -R agendaflow:agendaflow data

# Set environment variables
ENV PATH=/home/agendaflow/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Switch to non-root user
USER agendaflow

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Entrypoint script
COPY --chown=agendaflow:agendaflow docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
