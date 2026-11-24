# Dockerfile for HireLoop API & Workers

FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    python3-dev \
    curl \
    poppler-utils && \
    rm -rf /var/lib/apt/lists/*

ENV POETRY_HOME=/opt/poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s $POETRY_HOME/bin/poetry /usr/local/bin/poetry

WORKDIR /build
COPY pyproject.toml ./
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes && \
    pip install --no-cache-dir -r requirements.txt

# ---- Runtime stage ----
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    curl && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m appuser && mkdir -p /app/hireloop /app/data && chown -R appuser:appuser /app
USER appuser
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy repository into /app/hireloop so package name resolves correctly
COPY . /app/hireloop

ENV PYTHONPATH=/app
ENV DATA_STORAGE_DIR=/app/data

EXPOSE 8000

CMD ["uvicorn", "hireloop.apps.api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
