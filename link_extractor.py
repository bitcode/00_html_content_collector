from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
import re
import logging
from urllib.parse import urljoin
from scraper import normalize_url, is_valid_link, get_canonical_url

def extract_links(url, content, base_domain, start_path):
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
    logging.debug(f"Links extracted: {links}")
    logging.debug(f"Pagination links extracted: {pagination_links}")
    return links, pagination_links

def extract_pagination_links(soup, base_url):
    pagination_links = set()

    # Numbered pagination
    numbered_links = soup.find_all('a', href=True, text=re.compile(r'^\d+$'))

    # Next/Previous buttons
    next_prev_links = soup.find_all('a', href=True, text=re.compile(r'Next|Previous|Próximo|Anterior', re.IGNORECASE))

    # "Load More" buttons
    load_more_links = soup.find_all('a', href=True, text=re.compile(r'Load More|Show More|Ver Mais', re.IGNORECASE))

    # Combine all pagination links
    for link in numbered_links + next_prev_links + load_more_links:
        href = link['href']
        full_url = urljoin(base_url, href)
        pagination_links.add(full_url)

    return pagination_links

def extract_links_selenium(driver, base_domain, start_path):
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
    return links, pagination_links
