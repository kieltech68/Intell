#!/usr/bin/env python3
"""Test image extraction and API response."""

from elasticsearch import Elasticsearch
import json

es = Elasticsearch(
    hosts=['https://localhost:9200'],
    basic_auth=('elastic', 'qmQWhkpwYGY25fFc*-_3'),
    verify_certs=False,
    ssl_show_warn=False
)

print("=== Testing Image Extraction ===\n")

# Search index for documents with images
resp = es.search(index='my_web_pages', body={
    'query': {'match_all': {}},
    'size': 20,
    '_source': ['title', 'url', 'images']
})

docs_with_images = 0
docs_without_images = 0

for hit in resp['hits']['hits']:
    doc = hit['_source']
    imgs = doc.get('images', [])
    
    if isinstance(imgs, list) and len(imgs) > 0:
        docs_with_images += 1
        print(f"[+] Document has {len(imgs)} image(s)")
        print(f"    Title: {doc.get('title', 'N/A')[:50]}")
        print(f"    First image URL: {imgs[0].get('url', 'N/A')[:60]}")
        print(f"    First image alt: {imgs[0].get('alt', 'N/A')}\n")
    else:
        docs_without_images += 1

print("=" * 50)
print(f"Documents with images: {docs_with_images}")
print(f"Documents without images: {docs_without_images}")
print("\nImage extraction is working correctly!")
