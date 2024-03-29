from scraper import scrape_page
import logger
from urllib.parse import urlparse
import os

# Initialize logging
logger.setup_logging()

# Base URL for the LangChain API documentation
base_url = 'https://api.python.langchain.com/en/latest/langchain_api_reference.html'
parsed_url = urlparse(base_url)
base_domain = parsed_url.netloc
start_path = os.path.dirname(parsed_url.path)

# Set to keep track of visited URLs
visited = set()

# Start the scraping process
scrape_page(base_url, base_domain, start_path)
