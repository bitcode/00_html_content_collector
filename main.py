# ./00_html_content_collector/main.py
from config import MANIFEST, PROJECT_NAME, OUTPUT_DIR
import argparse
from scraper import start_scraping_from
from logger import setup_logging, log_error, log_info
from custom_exceptions import ScraperError, ConfigurationError, NetworkError

def main():
    parser = argparse.ArgumentParser(description=f"Web scraper for {PROJECT_NAME}")
    parser.add_argument("doc_name", help="The name of the documentation to scrape (as specified in core_manifest.yaml)")
    parser.add_argument("version", help="The version of the documentation to scrape")
    parser.add_argument("--initial_delay", type=int, default=3, help="Initial delay between requests in seconds")
    parser.add_argument("--max_workers", type=int, default=5, help="Maximum number of concurrent workers")
    args = parser.parse_args()

    try:
        # Initialize logging for this specific documentation and version
        loggers = setup_logging(OUTPUT_DIR, args.doc_name, args.version)

        # Get URL from manifest
        doc_url = next((source['url'] for source in MANIFEST['documentation_sources'] if source['name'] == args.doc_name), None)

        if not doc_url:
            raise ConfigurationError(f"Documentation source '{args.doc_name}' not found in core_manifest.yaml")

        # Start the scraping process
        log_info(loggers, f"Starting scrape for {args.doc_name} version {args.version} ({doc_url})")

        start_scraping_from(doc_url, args.doc_name, args.version, initial_delay=args.initial_delay, max_workers=args.max_workers)
        log_info(loggers, f"Completed scrape for {args.doc_name} version {args.version}")

    except ConfigurationError as e:
        log_error(loggers, f"Configuration error: {e.log_message()}")
    except NetworkError as e:
        log_error(loggers, f"Network error: {e.log_message()}")
    except ScraperError as e:
        log_error(loggers, f"Scraper error: {e.log_message()}")
    except Exception as e:
        log_error(loggers, f"Unexpected error: {str(e)}")
        log_error(loggers, ScraperError(f"Scraping process for {args.doc_name} version {args.version} failed"))
    finally:
        if 'loggers' in locals():
            log_info(loggers, "Scraping process completed")


if __name__ == "__main__":
    main()
