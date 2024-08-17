# ./00_html_content_collector/scheduled_scrape.py
import schedule
import time
from scraper import scrape_pages_concurrently, prioritize_pages, get_urls_to_scrape
from config import MANIFEST
from logger import setup_logging, log_error, log_info
from custom_exceptions import NetworkError, ParsingError, DatabaseError

# Initialize loggers
loggers = setup_logging(output_dir='logs', doc_name='scheduled_scrape', version='v1')

def run_scheduled_scrape():
    log_info(loggers, "Starting scheduled scrape")
    for doc_source in MANIFEST['documentation_sources']:
        doc_name = doc_source['name']
        for version in doc_source['versions']:
            base_url = doc_source['url']
            try:
                urls_to_scrape = get_urls_to_scrape(base_url)
                prioritized_urls = prioritize_pages(urls_to_scrape)
                scrape_pages_concurrently(prioritized_urls, doc_name, version)
                log_info(loggers, f"Completed scrape for {doc_name} version {version}")
            except NetworkError as e:
                log_error(loggers, f"Network error while scraping {doc_name} version {version}: {e.log_message()}")
            except ParsingError as e:
                log_error(loggers, f"Parsing error while scraping {doc_name} version {version}: {e.log_message()}")
            except DatabaseError as e:
                log_error(loggers, f"Database error while scraping {doc_name} version {version}: {e.log_message()}")
            except Exception as e:
                log_error(loggers, f"Unexpected error while scraping {doc_name} version {version}: {str(e)}")
    log_info(loggers, "Completed scheduled scrape")

def main():
    log_info(loggers, "Initializing scheduled scrape")
    # Schedule the scrape to run on the first day of every month at 02:00
    schedule.every().month.at("02:00").do(run_scheduled_scrape)

    while True:
        try:
            schedule.run_pending()
            time.sleep(3600)  # Sleep for 1 hour between checks
        except Exception as e:
            log_error(loggers, f"Error in scheduler: {str(e)}")
            time.sleep(3600)  # Sleep for 1 hour before retrying


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_info(loggers, "Scheduled scrape terminated by user")
    except Exception as e:
        log_error(loggers, f"Unexpected error in scheduled scrape: {str(e)}")
