"""
FastAPI application for searching indexed web pages in Elasticsearch.
"""

from fastapi import FastAPI, Query, HTTPException, Header
from fastapi.responses import JSONResponse
from elasticsearch import Elasticsearch
from typing import List, Optional
from contextlib import asynccontextmanager
import os
import time
import re
import math
from datetime import datetime

# Profanity filter list (basic)
PROFANITY_LIST = {
    'badword1', 'badword2', 'offensive', 'profane', 'adult', 'explicit'
}

# Simple stop-words list for query cleaning
STOP_WORDS = {
    'a', 'the', 'is', 'in', 'to', 'of', 'and', 'for', 'on', 'at', 'by', 'an', 'be', 'this', 'that'
}

def clean_query(query: str) -> str | None:
    """Clean a query string for logging:
    - lowercases
    - removes stop words
    - returns None for queries shorter than 3 characters after cleaning
    """
    if not query:
        return None
    q = query.lower()
    # keep only word characters
    tokens = re.findall(r"\w+", q)
    tokens = [t for t in tokens if t not in STOP_WORDS]
    cleaned = " ".join(tokens).strip()
    if len(cleaned) < 3:
        return None
    return cleaned

def check_instant_answer(query: str) -> Optional[dict]:
    """Check if query is a math expression or time request and return instant answer."""
    q = query.strip().lower()
    
    # Check for time-related queries
    if any(word in q for word in ['time', 'what time', 'current time', 'now']):
        current_time = datetime.now().strftime("%H:%M:%S")
        current_date = datetime.now().strftime("%Y-%m-%d")
        return {
            "type": "time",
            "answer": f"{current_date} {current_time}",
            "label": "Current Time"
        }
    
    # Check for math expressions (basic arithmetic)
    if any(op in q for op in ['+', '-', '*', '/', '%', '**']):
        try:
            # Safe eval for math expressions only
            result = eval(q, {"__builtins__": {}}, {})
            if isinstance(result, (int, float)):
                return {
                    "type": "math",
                    "expression": query,
                    "answer": str(result),
                    "label": "Calculation"
                }
        except:
            pass
    
    return None

def is_safe_content(content: str) -> bool:
    """Check if content contains profanity."""
    content_lower = content.lower()
    for word in PROFANITY_LIST:
        if word in content_lower:
            return False
    return True

# Elasticsearch connection parameters (read from environment for flexibility)
# Default to environment-provided host; support Bonsai-style URLs with embedded creds.
ES_RAW_HOST = os.getenv("ES_HOST", "elasticsearch:9200")
ES_USERNAME = os.getenv("ELASTIC_USER", os.getenv("ES_USERNAME", "elastic"))
ES_PASSWORD = os.getenv("ELASTIC_PASSWORD", os.getenv("ES_PASSWORD", "qmQWhkpwYGY25fFc*-_3"))
ES_INDEX = os.getenv("ES_INDEX", "my_web_pages")

# Robust ES_HOST parsing: ensure scheme and port; extract credentials from URL if present
from urllib.parse import urlparse, urlunparse
import certifi

try:
    raw = ES_RAW_HOST.strip()
    # If no scheme, assume https for secure cloud services like Bonsai
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw

    parsed = urlparse(raw)
    scheme = parsed.scheme or "https"
    username_in_url = parsed.username
    password_in_url = parsed.password
    hostname = parsed.hostname or ''
    port = parsed.port

    # Append default port if missing
    if port is None:
        netloc_host = hostname
        # preserve credentials if present
        if username_in_url and password_in_url:
            netloc = f"{username_in_url}:{password_in_url}@{netloc_host}:9200"
        else:
            netloc = f"{netloc_host}:9200"
    else:
        # rebuild netloc preserving credentials if any
        if username_in_url and password_in_url:
            netloc = f"{username_in_url}:{password_in_url}@{hostname}:{port}"
        else:
            netloc = f"{hostname}:{port}"

    ES_HOST = urlunparse((scheme, netloc, parsed.path or '', parsed.params or '', parsed.query or '', parsed.fragment or ''))
    print(f"Elasticsearch host set to: {ES_HOST}")
except Exception as e:
    print(f"Error parsing ES_HOST ('{ES_RAW_HOST}'): {e}")
    ES_HOST = os.getenv("ES_HOST", "http://elasticsearch:9200")
    print(f"Falling back to ES_HOST={ES_HOST}")

# If credentials were embedded in the URL, prefer them over empty env vars
try:
    parsed_for_creds = urlparse(ES_HOST)
    if not ES_USERNAME and parsed_for_creds.username:
        ES_USERNAME = parsed_for_creds.username
    if not ES_PASSWORD and parsed_for_creds.password:
        ES_PASSWORD = parsed_for_creds.password
except Exception:
    pass

# Initialize Elasticsearch client with TLS verification (Bonsai requires valid certs)
es_kwargs = {
    "hosts": [ES_HOST],
    "verify_certs": True,
    "ca_certs": certifi.where(),
    "ssl_show_warn": False,
}
if ES_USERNAME and ES_PASSWORD:
    es_kwargs["basic_auth"] = (ES_USERNAME, ES_PASSWORD)

es = Elasticsearch(**es_kwargs)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    try:
        if es.ping():
            print("✓ Connected to Elasticsearch at", ES_HOST)
        else:
            print("✗ Failed to connect to Elasticsearch")
    except Exception as e:
        print(f"✗ Elasticsearch error: {e}")
    yield
    # Shutdown
    print("Shutting down server...")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Web Search Engine API",
    description="Search indexed web pages using Elasticsearch",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Web Search Engine API",
        "endpoints": {
            "search": "/search?q=<query>",
            "docs": "/docs"
        }
    }

@app.get("/search")
def search(
    q: str = Query(..., min_length=1, description="Search query"),
    offset: int = Query(0, ge=0, description="Pagination offset for infinite scroll"),
    safe_search: bool = Query(True, description="Filter out unsafe content"),
    file_type: Optional[str] = Query(None, description="Filter by file type (html, pdf)")
):
    """
    Search indexed web pages with pagination, filtering, and instant answers.
    
    Args:
        q (str): Search query string (required)
        offset (int): Pagination offset for infinite scroll (default: 0)
        safe_search (bool): Filter out unsafe content (default: True)
        file_type (str): Filter by file type - 'html' or 'pdf' (optional)
        
    Returns:
        dict: Search results with title, url, instant_answer (optional), and more
        
    Raises:
        HTTPException: If search fails
    """
    try:
        # Check for instant answer first
        instant_answer = check_instant_answer(q)
        
        # Build query filters
        filters = []
        
        # Add safe_search filter (only apply if explicitly set to false)
        if not safe_search:
            filters.append({"term": {"is_safe": False}})
        
        # Add file_type filter if specified
        if file_type:
            filters.append({"term": {"file_type": file_type}})
        
        # Define multi-match query with field boosting and fuzzy search
        query_body = {
            "multi_match": {
                "query": q,
                "fields": ["title^3", "content"],
                "type": "best_fields",
                "operator": "or",
                "fuzziness": "AUTO",
                "prefix_length": 1
            }
        }
        
        # Build the search query with bool filters
        if filters:
            search_body = {
                "query": {
                    "bool": {
                        "must": query_body,
                        "filter": filters
                    }
                }
            }
        else:
            search_body = {"query": query_body}
        
        # Add highlighting
        search_body["highlight"] = {
            "fields": {
                "content": {
                    "fragment_size": 160,
                    "number_of_fragments": 1
                },
                "title": {
                    "fragment_size": 160,
                    "number_of_fragments": 1
                }
            },
            "pre_tags": ["<b>"],
            "post_tags": ["</b>"]
        }
        
        # Add pagination
        page_size = 10
        search_body["from"] = offset
        search_body["size"] = page_size

        # Add aggregation to compute related topics (significant text terms)
        search_body["aggs"] = {
            "related_topics": {
                "significant_text": {
                    "field": "content",
                    "size": 10
                }
            }
        }

        # Clean and log the search query to search_logs index
        try:
            cleaned = clean_query(q)
            if cleaned:
                log_doc = {
                    "query": cleaned,
                    "raw_query": q,
                    "timestamp": time.time()
                }
                es.index(index="search_logs", document=log_doc)
        except Exception as log_error:
            print(f"Warning: Failed to log search query: {log_error}")

        # Execute search
        response = es.search(index=ES_INDEX, body=search_body)
        results = response['hits']['hits']
        
        # Format results (Google-style)
        formatted_results = []
        for hit in results:
            source = hit['_source']
            url = source.get('url', 'No URL')
            
            # Extract display_url (domain name only, e.g., 'wikipedia.org')
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                display_url = parsed.netloc if parsed.netloc else url
            except:
                display_url = url
            
            # Extract snippet from highlight or fallback to first 160 chars
            snippet = ""
            if 'highlight' in hit and 'content' in hit['highlight']:
                snippet = hit['highlight']['content'][0] if hit['highlight']['content'] else ""
            
            if not snippet:
                # Fallback to first 160 characters of content
                content = source.get('content', '')
                snippet = content[:160] + "..." if len(content) > 160 else content
            
            formatted_results.append({
                "title": source.get('title', 'No Title'),
                "url": url,
                "display_url": display_url,
                "snippet": snippet,
                "favicon_url": source.get('favicon_url', ''),
                "images": source.get('images', []),
                "is_safe": source.get('is_safe', True),
                "file_type": source.get('file_type', 'html')
            })
        
        # Compute related topics using aggregation (exclude search tokens and stop words)
        related_topics = []
        try:
            buckets = response.get('aggregations', {}).get('related_topics', {}).get('buckets', [])
            # tokens to exclude (search terms + stop words)
            query_tokens = set(re.findall(r"\w+", q.lower()))
            exclusions = set([t.lower() for t in STOP_WORDS]) | query_tokens
            for bucket in buckets:
                term = bucket.get('key')
                if not term:
                    continue
                t = term.lower()
                if t in exclusions or len(t) < 3:
                    continue
                if term not in related_topics:
                    related_topics.append(term)
                if len(related_topics) >= 5:
                    break
        except Exception as agg_err:
            print(f"Related topics agg error: {agg_err}")

        # Build response with instant answer and related topics if available
        response_data = {
            "query": q,
            "total": len(formatted_results),
            "offset": offset,
            "results": formatted_results,
            "related_topics": related_topics
        }

        if instant_answer:
            response_data["instant_answer"] = instant_answer
        
        return response_data
        
    except Exception as e:
        print(f"Search error details: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Search error: {str(e)}"
        )

@app.get("/trending")
def trending():
    """Get trending search terms from user queries (last 24 hours)."""
    default_trending = [
        "Python",
        "Intell Search",
        "Web Crawling",
        "Elasticsearch",
        "AI"
    ]
    
    try:
        # Calculate timestamp for last 24 hours
        now = time.time()
        twenty_four_hours_ago = now - (24 * 60 * 60)
        
        # Query search_logs index with time range and terms aggregation
        agg_query = {
            "query": {
                "range": {
                    "timestamp": {
                        "gte": twenty_four_hours_ago
                    }
                }
            },
            "aggs": {
                "trending_queries": {
                    "terms": {
                        "field": "query.keyword",
                        "size": 5
                    }
                }
            },
            "size": 0
        }
        
        response = es.search(index="search_logs", body=agg_query)
        
        # Extract top 5 trending terms from aggregation
        buckets = response['aggregations']['trending_queries']['buckets']
        
        if buckets:
            trending_terms = [bucket['key'] for bucket in buckets]
            return {
                "trending": trending_terms
            }
        else:
            # Return default list if no data in last 24 hours
            return {
                "trending": default_trending
            }
    
    except Exception as e:
        # If search_logs index doesn't exist or aggregation fails, return default list
        print(f"Trending error: {str(e)}")
        return {
            "trending": default_trending
        }


@app.get("/suggest")
def suggest(q: str = Query(..., min_length=1, description="Partial title text for suggestions")):
    """Return up to 5 title suggestions using a prefix-style query on `title`."""
    try:
        # Use a match_phrase_prefix to provide type-as-you-go suggestions
        suggest_body = {
            "query": {
                "match_phrase_prefix": {
                    "title": {
                        "query": q
                    }
                }
            },
            "_source": ["title"],
            "size": 5
        }

        resp = es.search(index=ES_INDEX, body=suggest_body)
        hits = resp.get('hits', {}).get('hits', [])

        suggestions = []
        for h in hits:
            title = h.get('_source', {}).get('title')
            if title and title not in suggestions:
                suggestions.append(title)

        return {"query": q, "suggestions": suggestions}

    except Exception as e:
        print(f"Suggest error: {e}")
        raise HTTPException(status_code=500, detail=f"Suggest error: {str(e)}")

@app.get("/health")
def health():
    """Health check endpoint."""
    try:
        if es.ping():
            return {
                "status": "healthy",
                "elasticsearch": "connected",
            }
        else:
            return {
                "status": "unhealthy",
                "elasticsearch": "disconnected",
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


@app.post("/index-page")
async def index_page(request: dict, x_api_key: Optional[str] = Header(None)):
    """Index a single page via POST request from a trusted crawler.

    Security: Add an environment variable `API_KEY` and set it in your crawler headers
    as `x-api-key` to authorize indexing.

    Example payload (JSON):
    {
      "url": "https://example.com/page.html",
      "title": "Example Page",
      "content": "Full text content...",
      "favicon_url": "",
      "preview_image_url": "",
      "images": [],
      "file_type": "html"
    }

    Returns 201 on success with the indexed document id.
    """
    # Simple API key check
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Server misconfiguration: API_KEY not set")

    # Accept header as either 'x-api-key' in dict (FastAPI Header binding) or directly from request
    if x_api_key is None:
        # FastAPI didn't bind header (older style), try retrieving from environment or raw headers
        raise HTTPException(status_code=401, detail="Missing API key header 'x-api-key'")

    if x_api_key != api_key:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid API key")

    # Validate payload
    payload = request
    url = payload.get("url")
    content = payload.get("content", "")
    title = payload.get("title", url or "No title")
    if not url:
        raise HTTPException(status_code=400, detail="Missing required field: url")

    doc = {
        "url": url,
        "title": title,
        "content": content,
        "favicon_url": payload.get("favicon_url", ""),
        "preview_image_url": payload.get("preview_image_url", ""),
        "images": payload.get("images", []),
        "file_type": payload.get("file_type", "html"),
        "is_safe": is_safe_content(content),
        "timestamp": time.time(),
    }

    try:
        res = es.index(index=ES_INDEX, document=doc)
        return JSONResponse(
            status_code=201,
            content={
                "result": "indexed",
                "id": res.get("_id") if isinstance(res, dict) else None,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index document: {e}")

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        timeout_keep_alive=60,
        limit_concurrency=10
    )
