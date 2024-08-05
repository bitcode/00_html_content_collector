# ./00_html_content_collector/link_extractor.py
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
import re
from urllib.parse import urljoin
from scraper import normalize_url, is_valid_link, get_canonical_url
from custom_exceptions import ParsingError
from logger import setup_logging, log_error, log_info, log_debug

# Initialize loggers
loggers = setup_logging(output_dir='logs', doc_name='link_extractor', version='v1')

def extract_links(url, content, base_domain, start_path):
    try:
        if not isinstance(content, str):
            return set(), set()
        soup = BeautifulSoup(content, 'html.parser')
        links = set()
        pagination_links = extract_pagination_links(soup, url)
        for link in soup.find_all(['a', 'img', 'video', 'audio', 'source', 'iframe'], href=True, src=True):
            href = link.get('href') or link.get('src')
            full_url = urljoin(url, href)
            normalized_url = normalize_url(full_url)
            if is_valid_link(normalized_url, base_domain, start_path):
                links.add(normalized_url)
        log_debug(loggers, f"Links extracted: {links}")
        log_debug(loggers, f"Pagination links extracted: {pagination_links}")
        return links, pagination_links
    except Exception as e:
        log_error(loggers, ParsingError(f"Error extracting links from {url}: {str(e)}"))
        return set(), set()

def extract_pagination_links(soup, base_url):
    try:
        pagination_links = set()

        # Numbered pagination
        numbered_links = soup.find_all('a', href=True, text=re.compile(r'^\d+$'))

        # Next/Previous buttons
        next_prev_links = soup.find_all('a', href=True, text=re.compile(r'Next|Previous|Próximo|Anterior|Prev|Next Page|Previous Page', re.IGNORECASE))

        # First/Last buttons
        first_last_links = soup.find_all('a', href=True, text=re.compile(r'First|Last|Primeira|Última', re.IGNORECASE))

        # "Load More" buttons
        load_more_links = soup.find_all('a', href=True, text=re.compile(r'Load More|Show More|Ver Mais|Carregar Mais', re.IGNORECASE))

        # Combine all pagination links
        for link in numbered_links + next_prev_links + first_last_links + load_more_links:
            href = link['href']
            full_url = urljoin(base_url, href)
            pagination_links.add(full_url)

        return pagination_links
    except Exception as e:
        log_error(loggers, ParsingError(f"Error extracting pagination links from {base_url}: {str(e)}"))
        return set()

def extract_links_selenium(driver, base_domain, start_path):
    try:
        links = set()
        pagination_links = set()
        for a in driver.find_elements(By.TAG_NAME, 'a'):
            href = a.get_attribute('href')
            if href and is_valid_link(href, base_domain, start_path):
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                canonical_href = get_canonical_url(soup, href)
                links.add(canonical_href)
                if re.search(r'Next|Próximo|\d+', a.text):
                    pagination_links.add(canonical_href)
        log_info(loggers, f"Extracted {len(links)} links and {len(pagination_links)} pagination links using Selenium")
        return links, pagination_links
    except Exception as e:
        log_error(loggers, ParsingError(f"Error extracting links using Selenium: {str(e)}"))
        return set(), set()
