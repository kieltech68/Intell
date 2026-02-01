"""
Smart selective reindex script for Elasticsearch docs missing images, file_type, or is_safe.
- Finds docs missing any of these fields in `my_web_pages`.
- Fetches their URLs, re-extracts metadata using crawler helpers, and updates docs in-place.
- Usage: python reindex_missing_fields.py
"""
import os
from elasticsearch import Elasticsearch
from crawler import extract_images, extract_pdf_text, is_safe_content, clean_text
import requests

ES_HOST = os.environ.get("ES_HOST", "http://localhost:9200")
ES_USER = os.environ.get("ES_USER", "elastic")
ES_PASSWORD = os.environ.get("ES_PASSWORD", "changeme")
INDEX = "my_web_pages"

# Use verify_certs for production
VERIFY_CERTS = os.environ.get("VERIFY_CERTS", "false").lower() == "true"

es = Elasticsearch(
    ES_HOST,
    basic_auth=(ES_USER, ES_PASSWORD),
    verify_certs=VERIFY_CERTS
)

def find_missing_docs():
    # Find docs missing any of the target fields
    query = {
        "bool": {
            "should": [
                {"bool": {"must_not": {"exists": {"field": "images"}}}},
                {"bool": {"must_not": {"exists": {"field": "file_type"}}}},
                {"bool": {"must_not": {"exists": {"field": "is_safe"}}}},
            ]
        }
    }
    resp = es.search(index=INDEX, query=query, size=1000, _source=["url", "content"])
    return resp["hits"]["hits"]

def reindex_doc(doc):
    url = doc["_source"].get("url")
    content = doc["_source"].get("content", "")
    file_type = "html"
    images = []
    is_safe = True
    # Try to fetch and re-extract
    try:
        if url and url.lower().endswith(".pdf"):
            file_type = "pdf"
            pdf_text = extract_pdf_text(url)
            content = pdf_text or content
        else:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                html = r.text
                images = extract_images(html, url)
                content = clean_text(html)
        is_safe = is_safe_content(content)
    except Exception as e:
        print(f"Failed to re-extract {url}: {e}")
    # Update doc
    update_body = {"doc": {"images": images, "file_type": file_type, "is_safe": is_safe, "content": content}}
    es.update(index=INDEX, id=doc["_id"], body=update_body)
    print(f"Updated {url}")

def main():
    docs = find_missing_docs()
    print(f"Found {len(docs)} docs to reindex.")
    for doc in docs:
        reindex_doc(doc)

if __name__ == "__main__":
    main()
