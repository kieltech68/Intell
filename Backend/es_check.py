import requests
import os

ES_HOST = os.getenv('ES_HOST','https://intell-production.up.railway.app:9200')
ES_USER = os.getenv('ES_USERNAME','elastic')
ES_PASS = os.getenv('ES_PASSWORD','qmQWhkpwYGY25fFc*-_3')
INDEX = os.getenv('ES_INDEX','my_web_pages')

auth = (ES_USER, ES_PASS)

print(f"Querying ES host: {ES_HOST} (index={INDEX})\n")

def safe_get(url, **kwargs):
    try:
        r = requests.get(url, auth=auth, verify=False, timeout=10, **kwargs)
        print(url, "->", r.status_code)
        return r
    except Exception as e:
        print(url, "-> error:", e)
        return None

# List indices
resp = safe_get(f"{ES_HOST}/_cat/indices?v")
if resp is not None:
    print(resp.text[:1000])

# Run sample searches
for q in ("python", "intell"):
    print(f"\n--- Search for '{q}' in index '{INDEX}' ---")
    resp = safe_get(f"{ES_HOST}/{INDEX}/_search", params={"q": q, "size": 5})
    if resp is not None:
        try:
            data = resp.json()
            hits = data.get('hits', {}).get('hits', [])
            print(f"Found {len(hits)} hits (showing up to 5):")
            for h in hits:
                src = h.get('_source', {})
                title = src.get('title') or src.get('url') or src.get('text','')[:80]
                print(" -", title)
        except Exception as e:
            print("Could not parse JSON response:", e)

print("\nDone.")
