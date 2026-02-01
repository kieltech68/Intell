"""
Verify that pages were indexed in Elasticsearch.
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

try:
    # Get index stats
    stats = es.indices.stats(index=ES_INDEX)
    doc_count = stats['indices'][ES_INDEX]['primaries']['docs']['count']
    
    print(f"Index '{ES_INDEX}' contains {doc_count} documents\n")
    
    # Retrieve and display indexed documents
    response = es.search(index=ES_INDEX, query={"match_all": {}}, size=100)
    
    print("Indexed Pages:")
    print("-" * 80)
    for hit in response['hits']['hits']:
        source = hit['_source']
        url = source.get('url', 'N/A')
        title = source.get('title', 'N/A')
        content_preview = source.get('content', '')[:100] + "..."
        
        print(f"\nURL: {url}")
        print(f"Title: {title}")
        print(f"Content Preview: {content_preview}")
    
    print("\n" + "-" * 80)
    print(f"\nTotal documents indexed: {doc_count}")
    
except Exception as e:
    print(f"Error: {e}")
