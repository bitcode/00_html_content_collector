from scraper import scrape_page, convert_html_to_markdown
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

# Convert all HTML files to Markdown
downloaded_html_dir = os.path.join('downloaded_html', base_domain)
for root, dirs, files in os.walk(downloaded_html_dir):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            convert_html_to_markdown(filepath)
