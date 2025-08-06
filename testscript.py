import requests
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Setup headers to mimic a browser
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# Target URL
url = 'https://finance.yahoo.com/news/two-interactive-software-insiders-sell-140017765.html'

# Configure retries with backoff
retry_strategy = Retry(
    total=5,  # Total retries
    status_forcelist=[429, 500, 502, 503, 504],  # Retry on these codes
    allowed_methods=["HEAD", "GET", "OPTIONS"],
    backoff_factor=2  # Exponential backoff: 1st retry waits 2s, then 4s, etc.
)

# Mount adapter
adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("http://", adapter)
session.mount("https://", adapter)

# First request
response = session.get(url, headers=headers)

# Handle 429 (Too Many Requests) manually
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", 10))  # fallback to 10s
    print(f"Rate limited. Retrying after {retry_after} seconds...")
    time.sleep(retry_after)
    response = session.get(url, headers=headers)

# Save HTML if successful
if response.status_code == 200:
    with open('page.html', 'w', encoding='utf-8') as file:
        file.write(response.text)
    print("HTML downloaded successfully.")
else:
    print(f"Failed to download page. Status code: {response.status_code}")
