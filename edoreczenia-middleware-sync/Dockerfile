FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Create data directory
RUN mkdir -p /app/data

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Volume for persistent data
VOLUME ["/app/data"]

# Health check via status check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "from edoreczenia_sync.models import Database; db=Database('sqlite:///data/sync_state.db'); print('OK')" || exit 1

# Run
CMD ["python", "-m", "edoreczenia_sync.main", "--daemon"]
