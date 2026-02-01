"""
Test the search engine with a sample query.
"""

from elasticsearch import Elasticsearch

ES_HOST = "https://localhost:9200"
ES_USERNAME = "elastic"
ES_PASSWORD = "qmQWhkpwYGY25fFc*-_3"
ES_INDEX = "my_web_pages"

es = Elasticsearch(
    hosts=[ES_HOST],
    basic_auth=(ES_USERNAME, ES_PASSWORD),
    verify_certs=False,
    ssl_show_warn=False
)

print("=" * 80)
print("Web Search Engine - Test Query")
print("=" * 80)

query = "python"
search_body = {
    "query": {
        "multi_match": {
            "query": query,
            "fields": ["title^2", "content"],
            "fuzziness": "AUTO"
        }
    },
    "size": 5
}

response = es.search(index=ES_INDEX, body=search_body)
results = response['hits']['hits']

if results:
    print(f"\nSearch Query: '{query}'")
    print(f"Found {len(results)} result(s):\n")
    print("-" * 80)
    
    for idx, hit in enumerate(results, 1):
        source = hit['_source']
        score = hit['_score']
        title = source.get('title', 'No Title')
        url = source.get('url', 'No URL')
        
        print(f"\n{idx}. Title: {title}")
        print(f"   URL: {url}")
        print(f"   Score: {score:.4f}")
    
    print("\n" + "-" * 80)
else:
    print(f"\nNo results found for query: {query}")
