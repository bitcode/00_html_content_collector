import schedule
import time
from scraper import scrape_pages_concurrently, prioritize_pages
from config import MANIFEST

def run_scheduled_scrape():
    for doc_source in MANIFEST['documentation_sources']:
        doc_name = doc_source['name']
        for version in doc_source['versions']:
            base_url = doc_source['url']
            urls_to_scrape = get_urls_to_scrape(base_url)  # You'd need to implement this function
            prioritized_urls = prioritize_pages(urls_to_scrape)
            scrape_pages_concurrently(prioritized_urls, doc_name, version)

def main():
    schedule.every().day.at("02:00").do(run_scheduled_scrape)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
