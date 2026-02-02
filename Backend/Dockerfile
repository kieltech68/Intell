# Multi-stage Dockerfile for FastAPI app
FROM python:3.11-slim AS builder
WORKDIR /app

# Step 1: Copy from your computer into the container
COPY Backend/requirements.txt .

# Step 2: Install using the file (it is now just 'requirements.txt' inside the container)
RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip wheel --wheel-dir /wheels -r requirements.txt

# Final stage
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Copy wheels from builder
COPY --from=builder /wheels /wheels
COPY Backend/requirements.txt .
RUN python -m pip install --no-index --find-links=/wheels -r requirements.txt

# Copy the rest of your Python code
COPY Backend/ .

EXPOSE 8000

ENV ES_HOST=${ES_HOST:-http://elasticsearch:9200}
ENV ES_USERNAME=${ES_USERNAME:-elastic}
ENV ES_PASSWORD=${ES_PASSWORD:-changeme}

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
