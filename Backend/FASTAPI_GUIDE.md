# FastAPI Search Engine - Startup Guide

## Overview
This is a FastAPI application that provides a REST API for searching indexed web pages stored in Elasticsearch.

## Starting the Server

### Activate Virtual Environment
```powershell
.\\.venv\Scripts\Activate.ps1
```

### Run the Application
```powershell
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

Or simply:
```powershell
python app.py
```

The server will start on `http://0.0.0.0:8000`

## API Endpoints

### 1. Root Endpoint
**GET** `/`

Returns API information and available endpoints.

**Example:**
```
curl http://localhost:8000/
```

**Response:**
```json
{
  "message": "Web Search Engine API",
  "endpoints": {
    "search": "/search?q=<query>",
    "docs": "/docs"
  }
}
```

### 2. Search Endpoint
**GET** `/search?q=<query>`

Searches the indexed web pages using Elasticsearch multi-match query.

**Parameters:**
- `q` (required): Search query string

**Example:**
```
curl "http://localhost:8000/search?q=python"
```

**Response:**
```json
{
  "query": "python",
  "total": 1,
  "results": [
    {
      "title": "Welcome to Python.org",
      "url": "https://www.python.org",
      "content": "Notice: This page displays a fallback...",
      "score": 6.4288
    }
  ]
}
```

### 3. Health Check Endpoint
**GET** `/health`

Check Elasticsearch connection status.

**Example:**
```
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "elasticsearch": "connected"
}
```

### 4. Interactive API Documentation
**GET** `/docs`

Access the Swagger UI documentation at `http://localhost:8000/docs`

## Testing

### Test the API locally (without running server)
```powershell
python test_api.py
```

### Test from Android Phone
1. Find your computer's local IP address:
   ```powershell
   ipconfig
   ```
   Look for IPv4 Address (e.g., 192.168.1.x)

2. On your Android phone, make requests to:
   ```
   http://<your-ip>:8000/search?q=python
   ```

## Configuration

Edit `app.py` to change:
- Elasticsearch host: `ES_HOST`
- Username: `ES_USERNAME`
- Password: `ES_PASSWORD`
- Index name: `ES_INDEX`

## Requirements
- elasticsearch
- beautifulsoup4
- fastapi
- uvicorn
- httpx (for testing)

All are already installed in the virtual environment.
