FROM python:3.9-slim

WORKDIR /app

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libhdf5-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# CRITICAL: Copy models directory with trained model
COPY models/ ./models/

# Verify critical files exist
RUN echo "=== Verifying deployment files ===" && \
    ls -la /app/ && \
    echo "" && \
    echo "=== Models directory ===" && \
    ls -la /app/models/ && \
    test -f /app/models/emg_classifier.pkl || \
    (echo "ERROR: emg_classifier.pkl not found!" && exit 1) && \
    echo "✓ Model file verified"

# Create a startup script for better logging
RUN echo '#!/bin/bash\n\
echo "=== EMG Classifier API Starting ==="\n\
echo "Checking model file..."\n\
ls -lh /app/models/emg_classifier.pkl\n\
echo "Starting uvicorn server..."\n\
exec uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info --timeout-keep-alive 120' > /app/start.sh && \
    chmod +x /app/start.sh

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run using startup script
CMD ["/app/start.sh"]