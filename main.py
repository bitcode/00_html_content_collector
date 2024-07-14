# main.py
from config import MANIFEST, PROJECT_NAME, OUTPUT_DIR
import argparse
from scraper import scrape_page
import logger

def main():
    parser = argparse.ArgumentParser(description=f"Web scraper for {PROJECT_NAME}")
    parser.add_argument("doc_name", help="The name of the documentation to scrape (as specified in core_manifest.json)")
    parser.add_argument("version", help="The version of the documentation to scrape")
    parser.add_argument("--initial_delay", type=int, default=3, help="Initial delay between requests in seconds")
    args = parser.parse_args()

    # Initialize logging
    logger.setup_logging()

    # Get URL from manifest
    doc_url = next((source['url'] for source in MANIFEST['documentation_sources'] if source['name'] == args.doc_name), None)

    if not doc_url:
        logging.error(f"Documentation source '{args.doc_name}' not found in core_manifest.json")
        return

    # Start the scraping process
    logging.info(f"Starting scrape for {args.doc_name} version {args.version} ({doc_url})")
    scrape_page(doc_url, args.doc_name, args.version, initial_delay=args.initial_delay)
    logging.info(f"Completed scrape for {args.doc_name} version {args.version}")

if __name__ == "__main__":
    main()
