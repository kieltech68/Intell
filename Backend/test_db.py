"""
Test script to verify Elasticsearch connection.
"""

from elasticsearch import Elasticsearch

# Elasticsearch connection parameters
ES_HOST = "https://localhost:9200"
ES_USERNAME = "elastic"
ES_PASSWORD = "qmQWhkpwYGY25fFc*-_3"

def test_connection():
    """Test Elasticsearch connection and print cluster info."""
    try:
        # Create Elasticsearch client with SSL verification disabled for local dev instance
        es = Elasticsearch(
            hosts=[ES_HOST],
            basic_auth=(ES_USERNAME, ES_PASSWORD),
            verify_certs=False,
            ssl_show_warn=False
        )
        
        # Ping the cluster
        if es.ping():
            print("✓ Successfully connected to Elasticsearch!")
            
            # Get cluster information
            info = es.info()
            print("\nCluster Information:")
            print(f"  Cluster Name: {info['cluster_name']}")
            print(f"  Version: {info['version']['number']}")
            print(f"  Node Name: {info['name']}")
            print(f"  Lucene Version: {info['version']['lucene_version']}")
            
            return True
        else:
            print("✗ Failed to ping Elasticsearch cluster.")
            return False
            
    except Exception as e:
        print(f"✗ Connection error: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    print("Testing Elasticsearch connection...\n")
    success = test_connection()
    exit(0 if success else 1)
