import os
import time
import re
import requests
from bs4 import BeautifulSoup
import yfinance as yf
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

NUM_ARTICLES = 8
OUTPUT_DIR = "articles"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === SETUP SESSION WITH RETRIES ===
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

retry_strategy = Retry(
    total=5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"],
    backoff_factor=2
)

adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("http://", adapter)
session.mount("https://", adapter)


def safe_filename(title: str) -> str:
    """Convert article title to a safe filename."""
    return re.sub(r'[\\/*?:"<>|]', "", title).strip().replace(" ", "_")[:100] + ".txt"


def fetch_news(ticker: str, num_articles: int = NUM_ARTICLES, output_dir: str = OUTPUT_DIR):
    """Fetch news articles for a stock ticker and save them to text files."""
    ticker = ticker.upper()
    os.makedirs(output_dir, exist_ok=True)
    saved_files = []

    # === SEARCH FOR NEWS ===
    search_result = yf.Search(
        ticker,
        max_results=num_articles,
        news_count=num_articles,
        lists_count=num_articles,
        include_cb=True,
        include_nav_links=False,
        include_research=False,
        include_cultural_assets=False,
        enable_fuzzy_query=False,
        recommended=num_articles,
        timeout=30,
        raise_errors=True
    )

    articles = search_result.news[:num_articles]

    for idx, article in enumerate(articles):
        url = article["link"]
        title = article["title"]
        print(f"\n[{idx + 1}/{num_articles}] Processing: {title}\nURL: {url}")

        try:
            # Request the page
            response = session.get(url, headers=headers)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 10))
                print(f"Rate limited. Retrying in {retry_after} seconds...")
                time.sleep(retry_after)
                response = session.get(url, headers=headers)

            if response.status_code != 200:
                print(f"Failed to download article: {response.status_code}")
                continue

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            container = soup.find('div', class_='body yf-1ir6o1g')

            if not container:
                print("Article body not found.")
                continue

            # Extract text
            text_parts = []
            for tag in container.find_all(['p', 'h1', 'h2', 'h3', 'h4']):
                if tag.find_parent(attrs={'data-testid': 'inarticle-ad'}):
                    continue
                text = tag.get_text(strip=True)
                if text:
                    text_parts.append(text)

            if not text_parts:
                print("No article content found.")
                continue

            # Save to file
            filename = safe_filename(title)
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n\n'.join(text_parts))

            saved_files.append(filepath)
            print(f"Saved: {filepath}")

        except Exception as e:
            print(f"Error processing article: {e}")

    # === CLEANUP SHORT ARTICLES ===
    final_files = []
    for filepath in saved_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if len([line for line in lines if line.strip()]) < 3:
            os.remove(filepath)
            print(f"Deleted short article: {os.path.basename(filepath)}")
        else:
            final_files.append(filepath)

    return final_files
