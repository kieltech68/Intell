# Multi-stage Dockerfile for FastAPI app

# Builder stage
FROM python:3.11-slim AS builder
WORKDIR /app
# Fix: Tell Docker the file is inside the Backend folder
COPY Backend/requirements.txt ./
RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip wheel --wheel-dir /wheels -r Backend/requirements.txt

# Final stage
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Install from wheels
COPY --from=builder /wheels /wheels
# Fix: Tell Docker the file is inside the Backend folder
COPY Backend/requirements.txt ./
RUN python -m pip install --no-index --find-links=/wheels -r requirements.txt

# Copy application code from the Backend folder to the container's /app
COPY Backend/ /app

# Expose app port
EXPOSE 8000

# Environment variables
ENV ES_HOST=${ES_HOST:-http://elasticsearch:9200}
ENV ES_USERNAME=${ES_USERNAME:-elastic}
ENV ES_PASSWORD=${ES_PASSWORD:-changeme}

# Default command
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
