"""
Recursive web crawler script that fetches and indexes pages to Elasticsearch.
"""

import requests
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch
from urllib.parse import urljoin, urlparse
from collections import deque
import time
import re

try:
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# Profanity filter list (basic)
PROFANITY_LIST = {
    'badword1', 'badword2', 'offensive', 'profane', 'adult', 'explicit'
}

# Elasticsearch connection parameters
import os
# Elasticsearch connection parameters (read from environment for flexibility)
ES_HOST = os.getenv("ES_HOST", "https://localhost:9200")
ES_USERNAME = os.getenv("ELASTIC_USER", os.getenv("ES_USERNAME", "elastic"))
ES_PASSWORD = os.getenv("ELASTIC_PASSWORD", os.getenv("ES_PASSWORD", "qmQWhkpwYGY25fFc*-_3"))
ES_INDEX = os.getenv("ES_INDEX", "my_web_pages")

# Crawler configuration
MAX_DEPTH = 2
MAX_PAGES = 300
REQUEST_TIMEOUT = (5, 10)  # (connect_timeout, read_timeout)

# Disable urllib3 SSL warnings for local dev instance
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize Elasticsearch client
es = Elasticsearch(
    hosts=[ES_HOST],
    basic_auth=(ES_USERNAME, ES_PASSWORD),
    verify_certs=False,
    ssl_show_warn=False
)

# Seed URLs to crawl
SEED_URLS = [
    "https://www.python.org",
    "https://www.wikipedia.org",
    "https://www.github.com",
    "https://www.stackoverflow.com",
    "https://www.rust-lang.org"
]

def clean_text(text):
    """Clean and normalize text by removing extra whitespace."""
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text

def is_safe_content(content: str) -> bool:
    """Check if content contains profanity."""
    content_lower = content.lower()
    for word in PROFANITY_LIST:
        if word in content_lower:
            return False
    return True

def get_domain(url):
    """Extract domain from URL."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

def extract_pdf_text(pdf_url: str, session) -> str | None:
    """Extract text from a PDF URL using PyPDF2."""
    if not PDF_SUPPORT:
        return None
    
    try:
        response = session.get(pdf_url, timeout=REQUEST_TIMEOUT, verify=False)
        response.raise_for_status()
        
        from io import BytesIO
        pdf_file = BytesIO(response.content)
        reader = PdfReader(pdf_file)
        
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        return text.strip() if text else None
    except Exception as e:
        print(f"    Error extracting PDF: {type(e).__name__}")
        return None

def extract_links(url, html_content):
    """Extract all internal links from HTML content."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        links = set()
        domain = get_domain(url)
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Convert relative URLs to absolute
            absolute_url = urljoin(url, href)
            
            # Only keep internal links (same domain)
            if absolute_url.startswith(domain):
                # Remove fragments
                absolute_url = absolute_url.split('#')[0]
                if absolute_url:
                    links.add(absolute_url)
        
        return links
    except Exception as e:
        print(f"    Error extracting links: {type(e).__name__}")
        return set()

def extract_images(url, html_content):
    """Extract image URLs and alt-text from HTML content."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        images = []
        
        for img in soup.find_all('img'):
            src = img.get('src')
            alt = img.get('alt', '').strip()
            
            if src:
                # Convert relative URLs to absolute
                absolute_url = urljoin(url, src)
                images.append({
                    "url": absolute_url,
                    "alt": alt if alt else "No alt text"
                })
        
        return images
    except Exception as e:
        print(f"    Error extracting images: {type(e).__name__}")
        return []

def crawl_and_index(url, session):
    """
    Fetch a URL, extract content, and index it to Elasticsearch.
    
    Args:
        url (str): The URL to crawl
        session (requests.Session): HTTP session with configured timeouts
        
    Returns:
        tuple: (success: bool, links: set of internal URLs found)
    """
    try:
        print(f"  Crawling: {url}...", end=" ")
        
        # Check if URL points to a PDF
        is_pdf = url.lower().endswith('.pdf')
        
        # Handle PDF extraction
        if is_pdf and PDF_SUPPORT:
            pdf_text = extract_pdf_text(url, session)
            if pdf_text:
                title = urlparse(url).path.split('/')[-1]
                content = pdf_text[:50000]
                
                doc = {
                    "url": url,
                    "title": title,
                    "content": content,
                    "file_type": "pdf",
                    "is_safe": is_safe_content(content),
                    "favicon_url": "",
                    "preview_image_url": "",
                    "images": [],
                    "timestamp": time.time()
                }
                
                es.index(index=ES_INDEX, document=doc)
                print("[+] Indexed (PDF)")
                return True, set()
        
        # Fetch the page for HTML content
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        session.max_redirects = 5
        response = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT, 
                               allow_redirects=True, verify=False)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title_tag = soup.find('title')
        title = title_tag.get_text() if title_tag else "No title"
        title = clean_text(title)
        
        # Extract body text
        body_tag = soup.find('body')
        if body_tag:
            for script in body_tag(['script', 'style']):
                script.decompose()
            content = body_tag.get_text()
        else:
            content = soup.get_text()
        
        content = clean_text(content)
        
        # Limit content length
        if len(content) > 50000:
            content = content[:50000]
        
        # Extract favicon URL
        favicon_url = ""
        favicon_tag = soup.find('link', rel=['icon', 'shortcut icon'])
        if favicon_tag and favicon_tag.get('href'):
            favicon_url = urljoin(url, favicon_tag['href'])
        
        # Extract preview image URL (Open Graph)
        preview_image_url = ""
        og_image_tag = soup.find('meta', property='og:image')
        if og_image_tag and og_image_tag.get('content'):
            preview_image_url = urljoin(url, og_image_tag['content'])
        
        # Extract images with alt-text
        images = extract_images(url, response.content)
        
        # Prepare document for Elasticsearch
        doc = {
            "url": url,
            "title": title,
            "content": content,
            "favicon_url": favicon_url,
            "preview_image_url": preview_image_url,
            "images": images,
            "file_type": "html",
            "is_safe": is_safe_content(content),
            "timestamp": time.time()
        }
        
        # Index the document
        es.index(index=ES_INDEX, document=doc)
        print("[+] Indexed")
        
        # Extract internal links
        links = extract_links(url, response.content)
        return True, links
        
    except requests.exceptions.Timeout:
        print("[!] Timeout")
        return False, set()
    except requests.exceptions.ConnectionError:
        print("[!] Connection error")
        return False, set()
    except requests.exceptions.RequestException as e:
        print(f"[!] Request error: {type(e).__name__}")
        return False, set()
    except Exception as e:
        print(f"[!] Error: {type(e).__name__}")
        return False, set()

def recursive_crawl():
    """
    Perform recursive crawl using BFS (breadth-first search).
    Respects max_depth and max_pages limits.
    """
    print("=" * 70)
    print("Recursive Web Crawler - Elasticsearch Indexer")
    print("=" * 70)
    print(f"Target Index: {ES_INDEX}")
    print(f"Elasticsearch: {ES_HOST}")
    print(f"Max Depth: {MAX_DEPTH}, Max Pages: {MAX_PAGES}\n")
    
    # Verify Elasticsearch connection
    try:
        if not es.ping():
            print("[!] Failed to connect to Elasticsearch")
            return
        print("[+] Connected to Elasticsearch\n")
    except Exception as e:
        print(f"[!] Elasticsearch connection error: {e}")
        return
    
    # Initialize crawl state
    visited_urls = set()
    queue = deque()  # (url, depth) tuples
    session = requests.Session()
    successful = 0
    failed = 0
    
    # Add seed URLs to queue
    for url in SEED_URLS:
        queue.append((url, 0))
    
    print(f"Starting recursive crawl with {len(SEED_URLS)} seed URL(s):\n")
    
    # BFS crawl loop
    while queue and len(visited_urls) < MAX_PAGES:
        url, depth = queue.popleft()
        
        # Skip if already visited
        if url in visited_urls:
            continue
        
        visited_urls.add(url)
        
        # Skip if beyond max depth
        if depth > MAX_DEPTH:
            print(f"Skipping (depth={depth}): {url}")
            continue
        
        print(f"[Depth {depth}] [{len(visited_urls)}/{MAX_PAGES}]")
        
        # Crawl and index the page
        success, links = crawl_and_index(url, session)
        
        if success:
            successful += 1
            # Add discovered links to queue if within depth limit
            if depth < MAX_DEPTH:
                for link in links:
                    if link not in visited_urls and len(visited_urls) < MAX_PAGES:
                        queue.append((link, depth + 1))
        else:
            failed += 1
        
        time.sleep(1)  # Be respectful with requests
    
    # Print summary
    print("\n" + "=" * 70)
    print(f"Crawl Summary:")
    print(f"  Total pages visited: {len(visited_urls)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Queue remaining: {len(queue)}")
    print("=" * 70)
    
    # Check index stats
    try:
        stats = es.indices.stats(index=ES_INDEX)
        doc_count = stats['indices'][ES_INDEX]['primaries']['docs']['count']
        print(f"\n[+] Index '{ES_INDEX}' now contains {doc_count} documents")
    except Exception as e:
        print(f"\nNote: Could not retrieve index stats: {e}")

if __name__ == "__main__":
    recursive_crawl()
