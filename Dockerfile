# Production Dockerfile for HireLoop API
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    python3-dev \
    poppler-utils && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies using pre-generated requirements.txt for fast, reliable builds
COPY requirements.txt ./
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app

ENV PYTHONPATH=/app
ENV PORT=8000

EXPOSE 8000

# Start server dynamically on Render's assigned $PORT
CMD ["sh", "-c", "uvicorn hireloop.apps.api.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
