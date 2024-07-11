from scraper import scrape_page
import logger
from urllib.parse import urlparse
import os

# Initialize logging
logger.setup_logging()

# Base URL for the documentation website (change this as needed)
base_url = 'https://docs.opencv.org/4.10.0/'
parsed_url = urlparse(base_url)
base_domain = parsed_url.netloc
start_path = os.path.dirname(parsed_url.path)

# Start the scraping process
scrape_page(base_url, base_domain, start_path, delay=3)  # Increased delay to 3 seconds
