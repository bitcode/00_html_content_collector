# ./00_html_content_collector/scraper_core.py
from scraper import normalize_url, is_valid_link, cached_load_checksum, get_stored_headers, has_headers_changed, download_media_file, calculate_checksum, get_canonical_url, save_content, prioritize_pages, check_link_integrity, extract_links_selenium, save_page, update_partial_content, circuit_breaker, fetch_page, generate_optimized_diff, save_scrape_progress, setup_webdriver, save_link_integrity, time_to_save_state, process_link_integrity_results, worker, save_scrape_state, update_stored_headers, urlparse, VersionedContentHashManager, RetryExhaustedException
import os
import time
import requests
import concurrent.futures
from requests.exceptions import RequestException
from multiprocessing import Manager
from threading import Lock
from bs4 import BeautifulSoup
from config import OUTPUT_DIR
import PriorityQueue
from rate_limiter import DynamicRateLimiter
from logger import setup_logging, log_error, log_info, log_warning, log_debug
from custom_exceptions import NetworkError, ParsingError, DatabaseError, ContentChangedError, CircuitBreakerError

# Initialize loggers
loggers = setup_logging(output_dir='logs', doc_name='scraper_core', version='v1')

def scrape_single_page(url, doc_name, version, rate_limiter, hash_manager, visited, queue, driver, base_domain, start_path, link_integrity_results):
    normalized_url = normalize_url(url)
    if normalized_url not in visited and is_valid_link(normalized_url, base_domain, start_path):
        try:
            with rate_limiter.lock:
                rate_limiter.wait()

            start_time = time.time()

            # Load the existing checksum and headers
            existing_checksum = cached_load_checksum(normalized_url)
            existing_headers = get_stored_headers(normalized_url)

            if not has_headers_changed(url, existing_headers):
                log_info(loggers, f'Headers unchanged, skipping: {url}')
                return

            try:
                content_type = requests.head(url).headers.get('Content-Type', '').split(';')[0]
            except RequestException as e:
                raise NetworkError(f"Failed to fetch headers for {url}: {str(e)}", url=url)

            if content_type.startswith(('image/', 'audio/', 'video/', 'application/pdf')):
                download_media_file(url, doc_name, version)
                visited.add(url)
            else:
                @circuit_breaker
                def fetch_with_circuit_breaker():
                    return fetch_page(driver, url)

                try:
                    content = fetch_with_circuit_breaker()
                except RetryExhaustedException as e:
                    raise NetworkError(f"Max retries reached for {url}: {str(e)}", url=url)
                except CircuitBreakerError as e:
                    raise NetworkError(f"Circuit breaker is open. Skipping {url}: {str(e)}", url=url)
                except Exception as e:
                    raise NetworkError(f"Unexpected error while fetching {url}: {str(e)}", url=url)

                new_checksum = calculate_checksum(content)

                if existing_checksum != new_checksum:
                    soup = BeautifulSoup(content, 'html.parser')
                    canonical_url = get_canonical_url(soup, url)

                    if canonical_url != url:
                        log_info(loggers, f"Canonical URL found for {url}: {canonical_url}")
                        if canonical_url in visited:
                            log_info(loggers, f"Canonical URL {canonical_url} already visited, skipping.")
                            return
                        url = canonical_url  # Use the canonical URL from this point on

                    with hash_manager.lock:
                        old_hash_info = hash_manager.get_hash_info(doc_name, version, url)
                        if hash_manager.content_changed(doc_name, version, url, content):
                            visited.add(url)
                            log_info(loggers, f'Content changed, updating: {url}')

                            if old_hash_info:
                                # Generate diff using the new function
                                diff = generate_optimized_diff(old_hash_info['content'], content, doc_name, version)
                                try:
                                    update_partial_content(doc_name, version, url, diff)
                                except Exception as e:
                                    log_error(loggers, f"Partial update failed for {url}: {str(e)}")
                                    # Fallback to full content update
                                    save_content(content, url, doc_name, version, content_type)
                            else:
                                # Full save for new content
                                save_content(content, url, doc_name, version, content_type)

                            # Save to database
                            new_headers = {
                                'Last-Modified': driver.execute_script("return document.lastModified;"),
                                'ETag': driver.execute_script("return document.querySelector('meta[name=\"etag\"]')?.content;"),
                                'Content-Length': len(content)
                            }
                            try:
                                save_page(url, content, new_checksum, new_headers)
                            except Exception as e:
                                raise DatabaseError(f"Failed to save page {url}: {str(e)}", url=url)

                            # Extract links from rendered page
                            links, pagination_links = extract_links_selenium(driver, base_domain, start_path)

                            # Recalculate priorities for all links
                            all_links = links.union(pagination_links)
                            prioritized_links = prioritize_pages(all_links, hash_manager, doc_name, version)

                            for priority, link in prioritized_links:
                                if link not in visited:
                                    if link in pagination_links:
                                        priority *= 1.5  # Increase priority for pagination links
                                    queue.put((priority, link))

                            # Perform link integrity check for all links
                            for link in all_links:
                                integrity_result = check_link_integrity(link, url)
                                link_integrity_results.append(integrity_result)
                                save_link_integrity(integrity_result)
                        else:
                            log_info(loggers, f'Content unchanged, skipping: {url}')

                    # Update stored headers
                    update_stored_headers(url, new_headers)
                else:
                    log_info(loggers, f'Content unchanged, skipping: {url}')

                # Save scrape progress
                save_scrape_progress(url)

            with rate_limiter.lock:
                rate_limiter.update(time.time() - start_time)

        except NetworkError as e:
            log_error(loggers, f"Network error while scraping {url}: {e.log_message()}")
            with rate_limiter.lock:
                rate_limiter.backoff()
        except ParsingError as e:
            log_error(loggers, f"Parsing error while scraping {url}: {e.log_message()}")
        except DatabaseError as e:
            log_error(loggers, f"Database error while scraping {url}: {e.log_message()}")
        except ContentChangedError as e:
            log_warning(loggers, f"Content changed unexpectedly for {url}: {e.log_message()}")
        except Exception as e:
            log_error(loggers, f"Unexpected error while scraping {url}: {str(e)}")
            with rate_limiter.lock:
                rate_limiter.backoff()

def scrape_pages_concurrently(queue, doc_name, version, rate_limiter, hash_manager, visited, base_domain, start_path, link_integrity_results, max_workers=5):
    def worker_wrapper():
        driver = setup_webdriver()
        worker(queue, doc_name, version, rate_limiter, hash_manager, visited, driver, base_domain, start_path, link_integrity_results, loggers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(worker_wrapper) for _ in range(max_workers)]

        while not queue.empty():
            if time_to_save_state():
                save_scrape_state(doc_name, version, queue, visited)

            done, not_done = concurrent.futures.wait(futures, timeout=0, return_when=concurrent.futures.FIRST_COMPLETED)

            for future in done:
                futures.remove(future)
                futures.append(executor.submit(worker_wrapper))

        concurrent.futures.wait(futures)

    process_link_integrity_results(link_integrity_results, doc_name, version)

def start_scraping_from(url, doc_name, version, initial_delay=1, max_workers=5):
    log_info(loggers, f"Starting scrape from URL: {url}")
    try:
        parsed_url = urlparse(url)
        base_domain = parsed_url.netloc
        start_path = os.path.dirname(parsed_url.path)

        manager = Manager()
        visited = manager.Set()
        queue = PriorityQueue()
        link_integrity_results = manager.list()

        rate_limiter = DynamicRateLimiter(initial_delay=initial_delay)
        rate_limiter.lock = Lock()
        hash_manager = VersionedContentHashManager(OUTPUT_DIR)
        hash_manager.lock = Lock()

        normalized_url = normalize_url(url)
        try:
            response = requests.get(normalized_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            canonical_url = get_canonical_url(soup, normalized_url)

            # Extract initial links
            initial_links, _ = extract_links_selenium(setup_webdriver(), base_domain, start_path)

            # Prioritize initial links
            prioritized_links = prioritize_pages(initial_links, hash_manager, doc_name, version)

            # Add prioritized links to the queue
            for priority, link in prioritized_links:
                queue.put((priority, link))

        except RequestException as e:
            raise NetworkError(f"Error fetching start URL: {str(e)}", url=url)

        scrape_pages_concurrently(queue, doc_name, version, rate_limiter, hash_manager, visited, base_domain, start_path, link_integrity_results, max_workers)
    except NetworkError as e:
        log_error(loggers, f"Network error in start_scraping_from: {e.log_message()}")
    except Exception as e:
        log_error(loggers, f"Unexpected error in start_scraping_from: {str(e)}")
        raise
