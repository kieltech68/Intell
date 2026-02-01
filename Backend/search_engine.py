"""
Search engine script for querying indexed web pages in Elasticsearch.
"""

from elasticsearch import Elasticsearch

# Elasticsearch connection parameters
ES_HOST = "https://localhost:9200"
ES_USERNAME = "elastic"
ES_PASSWORD = "qmQWhkpwYGY25fFc*-_3"
ES_INDEX = "my_web_pages"

# Initialize Elasticsearch client
es = Elasticsearch(
    hosts=[ES_HOST],
    basic_auth=(ES_USERNAME, ES_PASSWORD),
    verify_certs=False,
    ssl_show_warn=False
)

def search_pages(query):
    """
    Perform a multi-match search against title and content fields.
    
    Args:
        query (str): The search query string
        
    Returns:
        list: List of search results
    """
    try:
        # Define multi-match query
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^2", "content"],  # title gets higher weight
                    "fuzziness": "AUTO"  # Allow fuzzy matching for typos
                }
            },
            "size": 5  # Return top 5 results
        }
        
        # Execute search
        response = es.search(index=ES_INDEX, body=search_body)
        return response['hits']['hits']
        
    except Exception as e:
        print(f"Search error: {e}")
        return []

def main():
    """Main function for the search engine."""
    print("=" * 80)
    print("Web Search Engine")
    print("=" * 80)
    
    # Verify Elasticsearch connection
    try:
        if not es.ping():
            print("✗ Failed to connect to Elasticsearch")
            return
        print("✓ Connected to Elasticsearch\n")
    except Exception as e:
        print(f"✗ Elasticsearch connection error: {e}")
        return
    
    # Main search loop
    while True:
        try:
            query = input("Enter search query: ").strip()
            
            if not query:
                print("Query cannot be empty. Please try again.\n")
                continue
            
            print("\nSearching...\n")
            
            # Perform search
            results = search_pages(query)
            
            # Display results
            if results:
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
                print("No results found for your query. Please try a different search.\n")
        
        except KeyboardInterrupt:
            print("\n\nExiting search engine. Goodbye!")
            break
        except Exception as e:
            print(f"Error during search: {e}\n")

if __name__ == "__main__":
    main()
