# Multi-stage Dockerfile for FastAPI app

# Builder stage: build wheels to speed up final image
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip wheel --wheel-dir /wheels -r requirements.txt

# Final stage
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Install from wheels produced in builder stage
COPY --from=builder /wheels /wheels
COPY requirements.txt ./
RUN python -m pip install --no-index --find-links=/wheels -r requirements.txt

# Copy application code
COPY . /app

# Expose app port
EXPOSE 8000

# Environment variables (can be overridden by docker-compose or env file)
ENV ES_HOST=${ES_HOST:-https://elasticsearch:9200}
ENV ES_USERNAME=${ES_USERNAME:-elastic}
ENV ES_PASSWORD=${ES_PASSWORD:-changeme}

# Default command
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
