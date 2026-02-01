"""
Test the FastAPI application without starting a server.
"""

import sys
sys.path.insert(0, r"C:\Users\Dell\OneDrive\New folder\Intell")

from fastapi.testclient import TestClient
from app import app

# Create a test client
client = TestClient(app)

print("=" * 80)
print("FastAPI Search Engine - Test")
print("=" * 80)

# Test root endpoint
print("\n1. Testing root endpoint:")
response = client.get("/")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# Test health endpoint
print("\n2. Testing health endpoint:")
response = client.get("/health")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# Test search endpoint
print("\n3. Testing search endpoint (query='python'):")
response = client.get("/search?q=python")
print(f"Status: {response.status_code}")
data = response.json()
print(f"Query: {data['query']}")
print(f"Total Results: {data['total']}")

if data['results']:
    print("\nResults:")
    print("-" * 80)
    for idx, result in enumerate(data['results'], 1):
        print(f"\n{idx}. Title: {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   Score: {result['score']:.4f}")
        print(f"   Content Preview: {result['content'][:100]}...")
else:
    print("No results found")

# Test search with another query
print("\n4. Testing search endpoint (query='github'):")
response = client.get("/search?q=github")
print(f"Status: {response.status_code}")
data = response.json()
print(f"Query: {data['query']}")
print(f"Total Results: {data['total']}")

if data['results']:
    for idx, result in enumerate(data['results'], 1):
        print(f"\n{idx}. Title: {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   Score: {result['score']:.4f}")

print("\n" + "=" * 80)
print("✓ All tests completed successfully!")
print("=" * 80)
