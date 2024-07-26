# Standard library imports
import os
import re
import json
import time
import logging
import hashlib
import functools
import mimetypes
import random
from functools import wraps
from requests import Session
from requests.exceptions import RequestException
from proxy_config import get_proxy_url
from collections import deque
from datetime import datetime
from statistics import mean
from urllib.parse import urlparse, urljoin, urlunparse, parse_qs, urlencode, urldefrag, unquote, quote, parse_qsl

# Third-party imports
import idna
import requests
import difflib
import xmltodict
import cairosvg
import extruct
import bleach
import html
import sqlite3
from sqlite3 import Error
from difflib import unified_diff
from bs4 import BeautifulSoup, Comment
from dateutil import parser
from w3lib.html import get_base_url
from langdetect import detect
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import ElementClickInterceptedException
import concurrent.futures
from multiprocessing import Manager
from threading import Lock
from queue import Queue

# Local imports
from config import MANIFEST, OUTPUT_DIR

class DynamicRateLimiter:
    def __init__(self, initial_delay=1, min_delay=0.5, max_delay=5, backoff_factor=1.5):
        self.current_delay = initial_delay
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.response_times = []

    def wait(self):
        time.sleep(self.current_delay)

    def update(self, response_time):
        self.response_times.append(response_time)
        if len(self.response_times) > 10:
            self.response_times.pop(0)

        avg_response_time = mean(self.response_times)

        if avg_response_time > 1:  # If average response time is over 1 second
            self.increase_delay()
        elif avg_response_time < 0.5 and self.current_delay > self.min_delay:
            self.decrease_delay()

    def increase_delay(self):
        self.current_delay = min(self.current_delay * self.backoff_factor, self.max_delay)

    def decrease_delay(self):
        self.current_delay = max(self.current_delay / self.backoff_factor, self.min_delay)

    def backoff(self):
        self.current_delay = min(self.current_delay * self.backoff_factor * 2, self.max_delay)


class PriorityQueue(Queue):
    def put(self, item, *args, **kwargs):
        return super().put(item, *args, **kwargs)

    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class VersionedContentHashManager:
    def __init__(self, dataset_root):
        self.dataset_root = dataset_root
        self.hash_dir = os.path.join(dataset_root, 'metadata', 'content_hashes')
        os.makedirs(self.hash_dir, exist_ok=True)
        self.hashes = self._load_hashes()

    def _get_hash_file(self, doc_name):
        return os.path.join(self.hash_dir, f"{doc_name}_hashes.json")

    def _load_hashes(self):
        hashes = {}
        for filename in os.listdir(self.hash_dir):
            if filename.endswith('_hashes.json'):
                doc_name = filename[:-12]  # Remove '_hashes.json'
                with open(os.path.join(self.hash_dir, filename), 'r') as f:
                    hashes[doc_name] = json.load(f)
        return hashes

    def _save_hashes(self, doc_name):
        with open(self._get_hash_file(doc_name), 'w') as f:
            json.dump(self.hashes[doc_name], f)

    def get_hash_info(self, doc_name, version, url):
        return self.hashes.get(doc_name, {}).get(version, {}).get(url)

    def update_hash_info(self, doc_name, version, url, content):
        if doc_name not in self.hashes:
            self.hashes[doc_name] = {}
        if version not in self.hashes[doc_name]:
            self.hashes[doc_name][version] = {}

        hash_info = {
            'hash': compute_hash(content),
            'last_modified': datetime.now().isoformat(),
            'size': len(content)
        }
        self.hashes[doc_name][version][url] = hash_info
        self._save_hashes(doc_name)

    def content_changed(self, doc_name, version, url, content):
        new_hash_info = {
            'hash': compute_hash(content),
            'size': len(content)
        }
        old_hash_info = self.get_hash_info(doc_name, version, url)
        if old_hash_info is None or old_hash_info['hash'] != new_hash_info['hash'] or old_hash_info['size'] != new_hash_info['size']:
            self.update_hash_info(doc_name, version, url, content)
            return True
        return False


class CircuitBreaker:
    def __init__(self, max_failures=5, reset_timeout=60):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "CLOSED"

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.reset_timeout:
                    self.state = "HALF-OPEN"
                else:
                    raise Exception("Circuit is OPEN")

            try:
                result = func(*args, **kwargs)
                if self.state == "HALF-OPEN":
                    self.state = "CLOSED"
                    self.failures = 0
                return result
            except Exception as e:
                self.failures += 1
                self.last_failure_time = time.time()
                if self.failures >= self.max_failures:
                    self.state = "OPEN"
                raise e
        return wrapper


# Usage
circuit_breaker = CircuitBreaker()


class Scraper:
    def __init__(self, proxies):
        self.session = Session()
        self.session.headers.update(get_custom_headers())
        self.proxy_manager = ProxyManager(proxies)

    def fetch_page(self, url):
        for _ in range(3):  # Try up to 3 times
            try:
                proxy = self.proxy_manager.get_proxy()
                response = self.session.get(url, proxies=proxy, timeout=10)
                response.raise_for_status()
                return response.text
            except requests.RequestException:
                self.proxy_manager.remove_current_proxy()
        raise Exception("Failed to fetch page after 3 attempts")


class ProxyManager:
    def __init__(self, max_failures=3, health_check_interval=300):
        self.proxy_url = get_proxy_url()
        self.max_failures = max_failures
        self.health_check_interval = health_check_interval
        self.failure_count = 0
        self.last_health_check = 0
        self.proxy = {
            'http': self.proxy_url,
            'https': self.proxy_url
        }

    def get_proxy(self):
        current_time = time.time()
        if current_time - self.last_health_check > self.health_check_interval:
            self.check_proxy_health()
        return self.proxy

    def check_proxy_health(self):
        try:
            response = requests.get('https://httpbin.org/ip', proxies=self.proxy, timeout=10)
            response.raise_for_status()
            self.failure_count = 0
            self.last_health_check = time.time()
            print(f"Proxy health check passed. IP: {response.json()['origin']}")
        except RequestException as e:
            self.failure_count += 1
            print(f"Proxy health check failed: {str(e)}")
            if self.failure_count >= self.max_failures:
                self.rotate_proxy()

    def rotate_proxy(self):
        # For Bright Data, rotation is automatic, so we just reset the failure count
        self.failure_count = 0
        print("Proxy rotated (Bright Data handles rotation automatically)")

    def handle_request_error(self, error):
        self.failure_count += 1
        print(f"Proxy request failed: {str(error)}")
        if self.failure_count >= self.max_failures:
            self.rotate_proxy()

def get_proxied_session():
    session = requests.Session()
    proxy_manager = ProxyManager()
    session.proxies = proxy_manager.get_proxy()

    original_request = session.request
    def proxied_request(*args, **kwargs):
        try:
            response = original_request(*args, **kwargs)
            response.raise_for_status()
            return response
        except RequestException as e:
            proxy_manager.handle_request_error(e)
            raise

    session.request = proxied_request
    return session


def create_connection():
    try:
        conn = sqlite3.connect('scraper_data.db')
        return conn
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None

def setup_webdriver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode (no GUI)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    proxy = ProxyManager().get_proxy()
    chrome_options.add_argument(f'--proxy-server={proxy["https"]}')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def normalize_html_structure(soup):
    # Ensure proper nesting and close unclosed tags
    # BeautifulSoup does this automatically when parsing

    # Remove empty tags
    for tag in soup.find_all():
        if len(tag.get_text(strip=True)) == 0 and len(tag.find_all()) == 0:
            tag.extract()

    return soup

def normalize_whitespace(text):
    # Remove excessive whitespace and normalize line breaks
    return re.sub(r'\s+', ' ', text).strip()

def normalize_character_encoding(soup):
    # Replace HTML entities with Unicode equivalents
    for text in soup.find_all(text=True):
        text.replace_with(html.unescape(str(text)))

    return soup

def normalize_urls(soup, base_url):
    for a in soup.find_all('a', href=True):
        a['href'] = urljoin(base_url, a['href'])

        # Remove tracking parameters
        parsed = urlparse(a['href'])
        qd = parse_qs(parsed.query, keep_blank_values=True)
        filtered = {k: v for k, v in qd.items() if not k.startswith('utm_')}
        parsed = parsed._replace(query=urlencode(filtered, doseq=True))
        a['href'] = urlunparse(parsed)

    return soup

def normalize_url(url):
    # Resolve protocol-relative URLs
    if url.startswith('//'):
        url = 'http:' + url

    # Expand shortened URLs
    url = expand_shortened_url(url)

    # Remove fragment
    url, _ = urldefrag(url)

    # Parse the URL
    parsed = urlparse(url)

    # Normalize scheme and domain
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Handle Internationalized Domain Names (IDN)
    try:
        netloc = netloc.encode('idna').decode('ascii')
    except idna.IDNAError:
        logging.warning(f"Failed to encode IDN: {netloc}")

    # WWW consistency
    if netloc.startswith('www.'):
        netloc = 'www.' + netloc.replace('www.', '')
    elif netloc.startswith('www1.') or netloc.startswith('www2.'):
        netloc = 'www.' + netloc[5:]

    # Handle default port removal
    if (scheme == 'http' and parsed.port == 80) or (scheme == 'https' and parsed.port == 443):
        netloc = parsed.hostname

    # Path normalization
    path = parsed.path

    # Resolve relative paths
    segments = path.split('/')
    resolved_segments = []
    for segment in segments:
        if segment == '.':
            continue
        elif segment == '..':
            if resolved_segments:
                resolved_segments.pop()
        else:
            resolved_segments.append(segment)
    path = '/'.join(resolved_segments)

    # Remove unnecessary slashes
    path = re.sub(r'//+', '/', path)

    # Trailing slash consistency
    if path:
        _, ext = os.path.splitext(path)
        if not ext:
            # It's a directory-like URL, add trailing slash if not present
            path = path.rstrip('/') + '/'
        else:
            # It's a file-like URL, remove trailing slash if present
            path = path.rstrip('/')
    else:
        # Empty path, add a single slash
        path = '/'

    # Decode unnecessary percent-encoded characters
    path = unquote(path)

    # Re-encode only the necessary characters
    path = quote(path, safe='/:@&=+$,')

    # Query parameter handling
    query = parsed.query
    if query:
        # Parse and sort query parameters
        query_params = parse_qsl(query)
        # Remove empty parameters, sort, and remove session IDs
        query_params = sorted((k, v) for k, v in query_params if v and not is_session_id(k))
        # Reconstruct the query string
        query = urlencode(query_params)

    # Reconstruct the URL
    normalized = urlunparse((
        scheme,
        netloc,
        path,
        parsed.params,
        query,
        ''  # Empty fragment
    ))

    return normalized

def expand_shortened_url(url):
    shortener_domains = ['bit.ly', 'tinyurl.com', 't.co', 'goo.gl']  # Add more as needed
    parsed = urlparse(url)
    if parsed.netloc in shortener_domains:
        try:
            response = requests.head(url, allow_redirects=True, timeout=5)
            return response.url
        except requests.RequestException:
            logging.warning(f"Failed to expand shortened URL: {url}")
    return url

def is_session_id(param):
    session_id_patterns = [
        r'^(session|sid)$',
        r'.*sessionid.*',
        r'^(s|sess)$',
        r'.*phpsessid.*',
        r'.*jsessionid.*',
        r'.*aspsessionid.*',
        r'.*cfid.*',
        r'.*cftoken.*',
    ]
    return any(re.match(pattern, param, re.IGNORECASE) for pattern in session_id_patterns)

def basic_content_cleaning(soup):
    # Remove HTML comments
    for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Strip out invisible text
    for hidden in soup.find_all(style=re.compile(r'display:\s*none')):
        hidden.extract()

    return soup

class RetryExhaustedException(Exception):
    pass

def get_content_filepath(doc_name, version, url):
    parsed_url = urlparse(url)
    local_file_path = parsed_url.path.lstrip('/')
    return os.path.join(get_version_path(doc_name, version), local_file_path)

def retry_with_exponential_backoff(func, max_retries=5, initial_delay=1, max_delay=60):
    def wrapper(*args, **kwargs):
        retries = 0
        delay = initial_delay
        while retries < max_retries:
            try:
                return func(*args, **kwargs)
            except RequestException as e:
                logging.warning(f"Network error occurred: {str(e)}")
                delay_factor = 2
            except TimeoutException as e:
                logging.warning(f"Timeout error occurred: {str(e)}")
                delay_factor = 1.5
            except WebDriverException as e:
                logging.warning(f"WebDriver error occurred: {str(e)}")
                delay_factor = 3
            except Exception as e:
                logging.error(f"Unexpected error occurred: {str(e)}")
                raise

            retries += 1
            if retries == max_retries:
                raise RetryExhaustedException(f"Max retries reached for {func.__name__}")

            wait_time = min(delay * (delay_factor ** retries), max_delay)
            logging.warning(f"Retrying in {wait_time:.2f} seconds...")
            time.sleep(wait_time)
    return wrapper

def extract_and_normalize_metadata(soup):
    metadata = {}

    # Extract and normalize dates
    for meta in soup.find_all('meta'):
        if 'name' in meta.attrs and 'content' in meta.attrs:
            if meta['name'] in ['date', 'pubdate', 'lastmod', 'modified']:
                try:
                    metadata[meta['name']] = parser.parse(meta['content']).isoformat()
                except ValueError:
                    logging.warning(f"Unable to parse date: {meta['content']}")

    # Normalize author names
    authors = soup.find_all('meta', attrs={'name': 'author'})
    if authors:
        metadata['authors'] = [author['content'].strip() for author in authors]

    return metadata

def detect_language(text):
    try:
        return detect(text)
    except Exception:  # It's better to catch specific exceptions if possible
        logging.warning("Failed to detect language", exc_info=True)
        return None

def clean_and_normalize_content(content, url):
    soup = BeautifulSoup(content, 'html.parser')

    soup = normalize_html_structure(soup)
    soup = normalize_character_encoding(soup)
    soup = normalize_urls(soup, url)
    soup = basic_content_cleaning(soup)

    normalized_text = normalize_whitespace(soup.get_text())

    metadata = extract_and_normalize_metadata(soup)
    metadata['language'] = detect_language(normalized_text)

    return str(soup), metadata

def is_acceptable_mime_type(mime_type):
    acceptable_types = [
        'text/html',
        'application/xhtml+xml',
        'application/xml',
        'text/xml',
        'text/plain',
    ]
    return any(mime_type.startswith(t) for t in acceptable_types)

def get_doc_name_from_url(url):
    return next((source['name'] for source in MANIFEST['documentation_sources'] if source['url'] in url), urlparse(url).netloc)

def compute_hash(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def handle_metadata_errors(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AttributeError as e:
            logging.warning(f"Metadata extraction error: {str(e)}")
            return None
    return wrapper

@handle_metadata_errors
def extract_title(soup):
    return soup.title.string

def extract_metadata(soup, url, html_content):
    metadata = {
        'url': url,
        'extraction_date': datetime.now().isoformat(),
        'title': extract_title(soup),
        'description': None,
        'keywords': None,
        'last_modified': None,
        'structured_data': None,  # New field for structured data
    }

    # Extract meta description
    desc_tag = soup.find('meta', attrs={'name': 'description'})
    if desc_tag:
        metadata['description'] = desc_tag.get('content')

    # Extract meta keywords
    keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
    if keywords_tag:
        metadata['keywords'] = keywords_tag.get('content')

    # Extract last modified date
    last_modified_tag = soup.find('meta', attrs={'name': 'last-modified'})
    if last_modified_tag:
        metadata['last_modified'] = last_modified_tag.get('content')

    # Extract Open Graph metadata
    og_tags = soup.find_all('meta', property=lambda x: x and x.startswith('og:'))
    metadata['og'] = {tag.get('property')[3:]: tag.get('content') for tag in og_tags}

    # Extract structured data
    base_url = get_base_url(html_content, url)
    structured_data = extruct.extract(
        html_content,
        base_url=base_url,
        syntaxes=['json-ld', 'microdata', 'rdfa']
    )

    # Process and clean the structured data
    cleaned_structured_data = {}
    for key, value in structured_data.items():
        if value:  # Only include non-empty data
            cleaned_structured_data[key] = value

    metadata['structured_data'] = cleaned_structured_data

    # Extract and parse last modified date
    last_modified_tag = soup.find('meta', attrs={'name': 'last-modified'})
    if last_modified_tag:
        try:
            parsed_date = parser.parse(last_modified_tag.get('content'))
            metadata['last_modified'] = parsed_date.isoformat()
        except ValueError:
            logging.warning(f"Unable to parse last modified date: {last_modified_tag.get('content')}")

    return metadata

class PriorityURL:
    def __init__(self, url, priority):
        self.url = url
        self.priority = priority

    def __lt__(self, other):
        return self.priority < other.priority

def calculate_priority(url, hash_manager, doc_name, version):
    hash_info = hash_manager.get_hash_info(doc_name, version, url)
    if not hash_info:
        return 1  # Highest priority for new pages
    last_modified = datetime.fromisoformat(hash_info['last_modified'])
    time_since_last_update = datetime.now() - last_modified
    return 1 / (time_since_last_update.total_seconds() + 1)

def preserve_mathjax(content):
    # Preserve inline math
    content = re.sub(r'\$(.+?)\$', r'<span class="math-inline">\1</span>', content)
    # Preserve block math
    content = re.sub(r'\$\$(.+?)\$\$', r'<div class="math-block">\1</div>', content, flags=re.DOTALL)
    return content

def preserve_katex(content):
    # Preserve inline KaTeX
    content = re.sub(r'\\(.+?)\\', r'<span class="katex-inline">\1</span>', content)
    # Preserve block KaTeX
    content = re.sub(r'\\\[(.+?)\\\]', r'<div class="katex-block">\1</div>', content, flags=re.DOTALL)
    return content

def preserve_latex(soup):
    for latex_element in soup.find_all('script', type='math/tex'):
        latex_element['class'] = latex_element.get('class', []) + ['preserved-latex']
        latex_element.string = f'$${latex_element.string}$$'

def is_valid_link(url, base_domain, start_path):
    normalized_url = normalize_url(url)
    parsed_url = urlparse(normalized_url)
    if parsed_url.scheme in ["http", "https"] and \
       parsed_url.netloc == base_domain and \
       parsed_url.path.startswith(start_path):
        canonical_url = get_canonical_url_from_head(normalized_url)
        if canonical_url != normalized_url:
            logging.debug(f"Using canonical URL: {canonical_url} instead of {normalized_url}")
            return is_valid_link(canonical_url, base_domain, start_path)
        logging.debug(f"Valid link found: {normalized_url}")
        return True
    logging.debug(f"Invalid link skipped: {normalized_url}")
    return False

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

def extract_and_convert_svgs(soup, base_dir):
    """Extract SVG elements and convert them to PNG."""
    svgs = soup.find_all('svg')
    for i, svg in enumerate(svgs):
        svg_content = str(svg)
        svg_file = os.path.join(base_dir, f'diagram_{i}.svg')
        png_file = os.path.join(base_dir, f'diagram_{i}.png')
        with open(svg_file, 'w') as file:
            file.write(svg_content)
        cairosvg.svg2png(url=svg_file, write_to=png_file)
        img_tag = soup.new_tag('img', src=f'diagram_{i}.png')
        svg.replace_with(img_tag)
        os.remove(svg_file)  # Clean up SVG file after conversion
        logging.debug(f"Converted SVG to PNG: {svg_file} to {png_file}")


def compute_content_diff(old_content, new_content):
    differ = difflib.Differ()
    diff = list(differ.compare(old_content.splitlines(), new_content.splitlines()))
    return '\n'.join(diff)

def update_partial_content(doc_name, version, url, diff):
    filepath = get_content_filepath(doc_name, version, url)
    with open(filepath, 'r', encoding='utf-8') as f:
        old_content = f.read()

    new_content = apply_diff(old_content, diff)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

def apply_diff(old_content, diff):
    lines = old_content.splitlines()
    for line in diff.splitlines():
        if line.startswith('+ '):
            lines.append(line[2:])
        elif line.startswith('- '):
            lines.remove(line[2:])
        elif line.startswith('? '):
            continue
        else:
            lines.append(line[2:])
    return '\n'.join(lines)

@retry_with_exponential_backoff
def fetch_svg_from_iframe(url, base_dir, index):
    response = requests.get(url)
    response.raise_for_status()
    svg_content = response.text

    # Save the SVG content to a temporary file
    svg_file = os.path.join(base_dir, f'temp_{index}.svg')
    with open(svg_file, 'w') as file:
        file.write(svg_content)

    # Convert the SVG to PNG
    png_file = os.path.join(base_dir, f'diagram_{index}.png')
    cairosvg.svg2png(url=svg_file, write_to=png_file)
    os.remove(svg_file)  # Clean up SVG file after conversion
    logging.debug(f"Converted iframe SVG to PNG: {svg_file} to {png_file}")

    return png_file

def extract_and_convert_iframe_svgs(soup, base_dir, base_url):
    """Extract SVG elements from iframes and convert them to PNG."""
    iframes = soup.find_all('iframe', src=True)
    for index, iframe in enumerate(iframes):
        src = iframe['src']
        full_svg_url = urljoin(base_url, src)
        try:
            png_file = fetch_svg_from_iframe(full_svg_url, base_dir, index)
            img_tag = soup.new_tag('img', src=os.path.basename(png_file))
            iframe.replace_with(img_tag)
            logging.debug(f"Replaced iframe with img tag: {img_tag}")
        except Exception as e:
            logging.error(f"Error processing iframe {src}: {e}")

def get_version_path(doc_name, version):
    return os.path.join(OUTPUT_DIR, 'docs', doc_name, version)

def save_content(content, url, doc_name, version, content_type):
    parsed_url = urlparse(url)
    local_file_path = parsed_url.path.lstrip('/')

    version_dir = get_version_path(doc_name, version)
    file_dir = os.path.join(version_dir, os.path.dirname(local_file_path))
    os.makedirs(file_dir, exist_ok=True)

    filename = os.path.basename(local_file_path) or 'index.html'
    if not filename.endswith(('.html', '.xml', '.txt')):
        extension = '.html' if content_type.startswith('text/html') else '.txt'
        filename += extension

    filepath = os.path.join(file_dir, filename)

    # Process content based on MIME type
    if content_type.startswith('text/html') or content_type.startswith('application/xhtml+xml'):
        cleaned_content, additional_metadata = clean_and_normalize_content(content, url)
        soup = BeautifulSoup(cleaned_content, 'html.parser')

        # Extract and download assets
        assets = extract_asset_links(soup, url)
        download_assets(assets, doc_name, version)

        # Update asset references in the HTML
        soup = update_asset_references(soup, assets, doc_name, version)

        process_html_content(soup, url, file_dir)
    elif content_type.startswith(('application/xml', 'text/xml')):
        soup = BeautifulSoup(content, 'xml')
        additional_metadata = {'content_type': 'xml'}
    else:  # Plain text
        soup = content
        additional_metadata = {'content_type': 'text'}

    save_file_content(soup, filepath)
    save_metadata(soup, url, filename, file_dir, additional_metadata)

def normalize_query_params(url):
    parsed = urlparse(url)
    # Parse and sort query parameters
    query_params = parse_qsl(parsed.query)
    # Remove empty parameters and sort
    query_params = sorted((k, v) for k, v in query_params if v)
    # Reconstruct the URL with sorted parameters
    return urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params,
         urlencode(query_params), parsed.fragment)
    )

def process_html_content(soup, url, directory):
    try:
        preserve_latex(soup)
        preserve_math_content(soup)
        preserve_code_blocks(soup)
        extract_and_convert_svgs(soup, directory)
        extract_and_convert_iframe_svgs(soup, directory, url)
    except Exception as e:
        logging.error(f"Error processing HTML content for {url}: {str(e)}")

def preserve_math_content(soup):
    for math_element in soup.find_all(['script', 'span', 'div'], class_=['math-inline', 'math-block', 'MathJax', 'katex-inline', 'katex-block']):
        math_element.string = preserve_mathjax(str(math_element))
        math_element.string = preserve_katex(str(math_element))

def preserve_code_blocks(soup):
    for code_block in soup.find_all(['pre', 'code']):
        code_block.string = bleach.clean(str(code_block), tags=['pre', 'code'], attributes={'class': []})

def save_file_content(soup, filepath):
    try:
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(str(soup))
        logging.info(f'Saved content to {filepath}')
    except Exception as e:
        logging.error(f"Error saving content to {filepath}: {str(e)}")

def save_metadata(soup, url, filename, directory, additional_metadata):
    try:
        metadata = extract_metadata(soup, url, str(soup))
        metadata.update(additional_metadata)

        metadata_filename = os.path.splitext(filename)[0] + '_metadata.json'
        metadata_filepath = os.path.join(directory, metadata_filename)
        with open(metadata_filepath, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Error extracting or saving metadata for {url}: {str(e)}")

@circuit_breaker
@retry_with_exponential_backoff
def fetch_page(driver, url):
    try:
        for key, value in get_custom_headers().items():
            driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {'headers': {key: value}})

        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Handle infinite scrolling
        scroll_page(driver)

        # Handle click-to-expand content
        expand_content(driver)

        return driver.page_source
    except TimeoutException:
        logging.warning(f"Timeout while loading {url}")
        raise
    except WebDriverException as e:
        logging.warning(f"WebDriver exception while fetching {url}: {str(e)}")
        raise

def scroll_page(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Wait to load page
        time.sleep(2)

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

        # Optional: implement a maximum scroll limit
        if last_height > 50000:  # Example: stop after 50000 pixels
            logging.info("Reached maximum scroll limit")
            break

def expand_content(driver):
    # List of common class names or IDs for expandable content
    expandable_selectors = [
        ".show-more", ".read-more", ".expand", "[id*='expand']", "[class*='expand']",
        "[aria-expanded='false']", ".collapsed", ".toggle", ".accordion-header"
    ]

    for selector in expandable_selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        for element in elements:
            try:
                if element.is_displayed() and element.is_enabled():
                    driver.execute_script("arguments[0].click();", element)
                    time.sleep(1)  # Wait for content to expand
            except ElementClickInterceptedException:
                logging.warning(f"Could not click element: {selector}")
            except Exception as e:
                logging.error(f"Error expanding content: {str(e)}")

def calculate_checksum(content):
    return hashlib.md5(content.encode()).hexdigest()

def has_page_changed(url, current_content):
    # Load previous checksum from storage
    previous_checksum = load_checksum(url)
    current_checksum = calculate_checksum(current_content)
    return previous_checksum != current_checksum

def scrape_page(base_url, doc_name, version, initial_delay=1):
    parsed_url = urlparse(base_url)
    base_domain = parsed_url.netloc
    start_path = os.path.dirname(parsed_url.path)

    visited = set()
    sitemap_urls = parse_sitemap(base_url)
    queue = deque(sitemap_urls + [base_url])
    rate_limiter = DynamicRateLimiter(initial_delay=initial_delay)
    hash_manager = VersionedContentHashManager(OUTPUT_DIR)

    driver = setup_webdriver()
    circuit_breaker = CircuitBreaker()

    try:
        while queue:
            url = queue.popleft()
            if url not in visited and is_valid_link(url, base_domain, start_path):
                try:
                    rate_limiter.wait()
                    start_time = time.time()

                    @circuit_breaker
                    def fetch_with_circuit_breaker():
                        return fetch_page(driver, url)

                    try:
                        content = fetch_with_circuit_breaker()
                    except Exception as e:
                        if isinstance(e, RetryExhaustedException):
                            logging.error(f"Max retries reached for {url}: {str(e)}")
                        elif str(e) == "Circuit is OPEN":
                            logging.error(f"Circuit breaker is open. Skipping {url}")
                        else:
                            logging.error(f"Unexpected error while fetching {url}: {str(e)}")
                        continue

                    content_type = 'text/html'  # Assume HTML for rendered content

                    response_time = time.time() - start_time
                    rate_limiter.update(response_time)

                    if hash_manager.content_changed(doc_name, version, url, content):
                        visited.add(url)
                        logging.info(f'Content changed, updating: {url}')
                        save_content(content, url, doc_name, version, content_type)

                        # Extract links from rendered page
                        links = extract_links_selenium(driver, base_domain, start_path)
                        for link in links:
                            if link not in visited:
                                queue.append(link)
                    else:
                        logging.info(f'Content unchanged, skipping: {url}')

                except RequestException as e:
                    logging.error(f"Network error while scraping {url}: {str(e)}")
                    rate_limiter.backoff()
                except Exception as e:
                    logging.error(f"Unexpected error while scraping {url}: {str(e)}")
                    rate_limiter.backoff()

    finally:
        driver.quit()

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

@retry_with_exponential_backoff
def parse_sitemap(base_url):
    sitemap_url = urljoin(base_url, 'sitemap.xml')
    try:
        response = requests.get(sitemap_url)
        response.raise_for_status()  # Raise an exception for bad status codes

        sitemap_dict = xmltodict.parse(response.content)

        urls = []
        if 'urlset' in sitemap_dict:
            # Standard sitemap
            for url in sitemap_dict['urlset']['url']:
                urls.append(url['loc'])
        elif 'sitemapindex' in sitemap_dict:
            # Sitemap index file
            for sitemap in sitemap_dict['sitemapindex']['sitemap']:
                urls.extend(parse_sitemap(sitemap['loc']))

        return urls
    except requests.RequestException as e:
        logging.error(f"Error fetching sitemap from {sitemap_url}: {e}")
        return []
    except xmltodict.expat.ExpatError as e:
        logging.error(f"Error parsing sitemap XML from {sitemap_url}: {e}")
        return []

def scrape_single_page(url, doc_name, version, rate_limiter, hash_manager, visited, queue, driver, base_domain, start_path, link_integrity_results):
    normalized_url = normalize_url(url)
    if normalized_url not in visited and is_valid_link(normalized_url, base_domain, start_path):
        try:
            with rate_limiter.lock:
                rate_limiter.wait()

            start_time = time.time()

            content_type = requests.head(url).headers.get('Content-Type', '').split(';')[0]

            if content_type.startswith(('image/', 'audio/', 'video/', 'application/pdf')):
                download_media_file(url, doc_name, version)
                visited.add(url)
            else:
                @circuit_breaker
                def fetch_with_circuit_breaker():
                    return fetch_page(driver, url)
                try:
                    content = fetch_with_circuit_breaker()
                except Exception as e:
                    if isinstance(e, RetryExhaustedException):
                        logging.error(f"Max retries reached for {url}: {str(e)}")
                    elif str(e) == "Circuit is OPEN":
                        logging.error(f"Circuit breaker is open. Skipping {url}")
                    else:
                        logging.error(f"Unexpected error while fetching {url}: {str(e)}")
                    return

                soup = BeautifulSoup(content, 'html.parser')
                canonical_url = get_canonical_url(soup, url)

                if canonical_url != url:
                    logging.info(f"Canonical URL found for {url}: {canonical_url}")
                    if canonical_url in visited:
                        logging.info(f"Canonical URL {canonical_url} already visited, skipping.")
                        return
                    url = canonical_url  # Use the canonical URL from this point on

                with hash_manager.lock:
                    old_hash_info = hash_manager.get_hash_info(doc_name, version, url)
                    if hash_manager.content_changed(doc_name, version, url, content):
                        visited.add(url)
                        logging.info(f'Content changed, updating: {url}')

                        if old_hash_info:
                            # Perform partial update
                            diff = compute_content_diff(old_hash_info['content'], content)
                            update_partial_content(doc_name, version, url, diff)
                        else:
                            # Full save for new content
                            save_content(content, url, doc_name, version, content_type)

                        # Save to database
                        checksum = calculate_checksum(content)
                        save_page(url, content, checksum)

                        # Extract links from rendered page
                        links, pagination_links = extract_links_selenium(driver, base_domain, start_path)
                        for link in links.union(pagination_links):
                            if link not in visited:
                                priority = calculate_priority(link, hash_manager, doc_name, version)
                                queue.put((priority, link))
                            # Perform link integrity check
                            integrity_result = check_link_integrity(link, url)
                            link_integrity_results.append(integrity_result)
                            save_link_integrity(integrity_result)
                    else:
                        logging.info(f'Content unchanged, skipping: {url}')

                # Save scrape progress
                save_scrape_progress(url)

            with rate_limiter.lock:
                rate_limiter.update(time.time() - start_time)

        except RequestException as e:
            logging.error(f"Network error while scraping {url}: {str(e)}")
            with rate_limiter.lock:
                rate_limiter.backoff()
        except Exception as e:
            logging.error(f"Unexpected error while scraping {url}: {str(e)}")
            with rate_limiter.lock:
                rate_limiter.backoff()

def worker(queue, doc_name, version, rate_limiter, hash_manager, visited, driver, base_domain, start_path, link_integrity_results):
    while True:
        try:
            priority, url = queue.get(timeout=1)  # Unpack both priority and URL
            normalized_url = normalize_url(url)
            soup = BeautifulSoup(requests.get(normalized_url).content, 'html.parser')
            canonical_url = get_canonical_url(soup, normalized_url)
            if canonical_url != normalized_url:
                logging.info(f"Canonical URL found: {canonical_url} for {normalized_url}")
                normalized_url = canonical_url
            scrape_single_page(normalized_url, doc_name, version, rate_limiter, hash_manager, visited, queue, driver, base_domain, start_path, link_integrity_results)
        except queue.Empty:
            break  # Exit if the queue is empty
        finally:
            queue.task_done()

def get_canonical_url_from_head(url):
    try:
        response = requests.head(url, allow_redirects=True)
        if 'Link' in response.headers:
            links = requests.utils.parse_header_links(response.headers['Link'])
            for link in links:
                if link.get('rel') == 'canonical':
                    return link.get('url')
    except requests.RequestException:
        logging.warning(f"Error checking canonical URL for {url}")
    return url

def save_scrape_state(doc_name, version, queue, visited):
    state = {
        'queue': list(queue.queue),
        'visited': list(visited)
    }
    state_file = os.path.join(OUTPUT_DIR, 'scrape_states', f'{doc_name}_{version}_state.json')
    with open(state_file, 'w') as f:
        json.dump(state, f)

last_save_time = time.time()

def time_to_save_state():
    global last_save_time
    current_time = time.time()
    if current_time - last_save_time > 300:  # Save every 5 minutes
        last_save_time = current_time
        return True
    return False

def load_scrape_state(doc_name, version):
    state_file = os.path.join(OUTPUT_DIR, 'scrape_states', f'{doc_name}_{version}_state.json')
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            state = json.load(f)
        return state
    return None

def scrape_pages_concurrently(queue, doc_name, version, rate_limiter, hash_manager, visited, base_domain, start_path, link_integrity_results, max_workers=5):
    def worker_wrapper():
        driver = setup_webdriver()
        worker(queue, doc_name, version, rate_limiter, hash_manager, visited, driver, base_domain, start_path, link_integrity_results)

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

def check_link_integrity(url, base_url):
    try:
        proxy = ProxyManager().get_proxy()
        headers = get_custom_headers()
        response = requests.head(url, allow_redirects=True, timeout=10, proxies=proxy, headers=headers)
        result = {
            'url': url,
            'status_code': response.status_code,
            'final_url': response.url,
            'is_redirect': len(response.history) > 0,
            'content_type': response.headers.get('Content-Type', ''),
            'is_internal': urlparse(url).netloc == urlparse(base_url).netloc,
        }

        if result['is_redirect']:
            result['redirect_chain'] = [r.url for r in response.history] + [response.url]

        if result['is_internal'] and '#' in url:
            # Check if anchor exists for internal links
            anchor = url.split('#')[-1]
            page_content = requests.get(url, proxies=proxy, headers=headers).text
            soup = BeautifulSoup(page_content, 'html.parser')
            result['anchor_exists'] = bool(soup.find(id=anchor) or soup.find('a', {'name': anchor}))

        return result
    except requests.RequestException as e:
        return {
            'url': url,
            'error': str(e),
            'is_internal': urlparse(url).netloc == urlparse(base_url).netloc,
        }

def process_link_integrity_results(link_integrity_results, doc_name, version):
    # Convert the shared list to a regular list
    results = list(link_integrity_results)

    # Process the results (e.g., identify broken links, redirects, etc.)
    broken_links = [r for r in results if r.get('status_code', 0) >= 400]
    redirects = [r for r in results if r.get('is_redirect', False)]
    missing_anchors = [r for r in results if r.get('is_internal', False) and not r.get('anchor_exists', True)]

    # Save the results
    output_dir = os.path.join(OUTPUT_DIR, 'link_integrity', doc_name, version)
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, 'link_integrity_report.json'), 'w') as f:
        json.dump({
            'all_links': results,
            'broken_links': broken_links,
            'redirects': redirects,
            'missing_anchors': missing_anchors
        }, f, indent=2)

    logging.info(f"Link integrity report saved for {doc_name} version {version}")
    logging.info(f"Total links: {len(results)}, Broken: {len(broken_links)}, Redirects: {len(redirects)}, Missing anchors: {len(missing_anchors)}")

def get_canonical_url(soup, url):
    canonical_tag = soup.find('link', rel='canonical')
    if canonical_tag and canonical_tag.get('href'):
        canonical_url = canonical_tag['href']
        # Ensure the canonical URL is absolute
        return urljoin(url, canonical_url)
    return url  # If no canonical URL is specified, return the original URLs

def download_media_file(url, doc_name, version):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', '').split(';')[0]
        file_extension = mimetypes.guess_extension(content_type) or ''

        parsed_url = urlparse(url)
        local_file_path = parsed_url.path.lstrip('/')
        if not local_file_path.endswith(file_extension):
            local_file_path += file_extension

        file_path = os.path.join(get_version_path(doc_name, version), local_file_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logging.info(f"Downloaded media file: {url} to {file_path}")
    except Exception as e:
        logging.error(f"Error downloading media file {url}: {str(e)}")

def extract_asset_links(soup, base_url):
    assets = {
        'css': set(),
        'js': set(),
        'images': set(),
        'math': set()
    }

    # Extract CSS links
    for link in soup.find_all('link', rel='stylesheet'):
        assets['css'].add(urljoin(base_url, link.get('href')))

    # Extract JS links
    for script in soup.find_all('script', src=True):
        assets['js'].add(urljoin(base_url, script.get('src')))

    # Extract image links
    for img in soup.find_all('img', src=True):
        assets['images'].add(urljoin(base_url, img.get('src')))

    # Extract MathJax configuration
    for script in soup.find_all('script'):
        if 'MathJax.Hub.Config' in script.string:
            match = re.search(r'MathJax\.Hub\.Config\((.*?)\)', script.string, re.DOTALL)
            if match:
                config = json.loads(match.group(1))
                if 'extensions' in config:
                    for ext in config['extensions']:
                        assets['math'].add(urljoin(base_url, f'mathjax/extensions/{ext}.js'))

                # Add MathJax core
                assets['js'].add(urljoin(base_url, 'mathjax/MathJax.js'))

    return assets

def download_asset(url, save_path):
    try:
        response = requests.get(url)
        response.raise_for_status()
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'wb') as f:
            f.write(response.content)
        logging.info(f"Downloaded asset: {url} to {save_path}")
    except Exception as e:
        logging.error(f"Error downloading asset {url}: {str(e)}")

def download_assets(assets, doc_name, version):
    base_path = get_version_path(doc_name, version)
    for asset_type, urls in assets.items():
        for url in urls:
            parsed_url = urlparse(url)
            local_path = os.path.join(base_path, 'assets', asset_type, parsed_url.path.lstrip('/'))
            download_asset(url, local_path)

def update_asset_references(soup, assets, doc_name, version):
    base_path = get_version_path(doc_name, version)

    for link in soup.find_all('link', rel='stylesheet'):
        if link.get('href') in assets['css']:
            link['href'] = os.path.relpath(os.path.join(base_path, 'assets', 'css', urlparse(link['href']).path.lstrip('/')), base_path)

    for script in soup.find_all('script', src=True):
        if script.get('src') in assets['js']:
            script['src'] = os.path.relpath(os.path.join(base_path, 'assets', 'js', urlparse(script['src']).path.lstrip('/')), base_path)

    for img in soup.find_all('img', src=True):
        if img.get('src') in assets['images']:
            img['src'] = os.path.relpath(os.path.join(base_path, 'assets', 'images', urlparse(img['src']).path.lstrip('/')), base_path)

    return soup

def extract_pagination_links(soup, base_url):
    pagination_links = set()
    # Look for common pagination patterns
    pagination_elements = soup.find_all('a', href=True, text=re.compile(r'Next|Próximo|\d+'))
    for element in pagination_elements:
        href = element['href']
        full_url = urljoin(base_url, href)
        pagination_links.add(full_url)
    return pagination_links

def get_custom_headers():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'
    ]

    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',  # Do Not Track Request Header
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    return headers

def update_content(old_content, new_content):
    diff = list(unified_diff(old_content.splitlines(), new_content.splitlines()))
    if diff:
        # Apply the diff to the stored content
        # This is a simplified example; you'd need a more robust diff application
        return new_content
    return old_content

def init_db():
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS pages
                         (url TEXT PRIMARY KEY, content TEXT, checksum TEXT, last_updated TIMESTAMP)''')
            c.execute('''CREATE TABLE IF NOT EXISTS scrape_progress
                         (url TEXT PRIMARY KEY, last_scraped TIMESTAMP)''')
            c.execute('''CREATE TABLE IF NOT EXISTS link_integrity
                         (url TEXT PRIMARY KEY, status_code INTEGER, is_redirect BOOLEAN, final_url TEXT, 
                          content_type TEXT, is_internal BOOLEAN, anchor_exists BOOLEAN)''')
            conn.commit()
        except Error as e:
            print(f"Error creating database tables: {e}")
        finally:
            conn.close()
    else:
        print("Error! Cannot create the database connection.")

def save_page(url, content, checksum):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO pages VALUES (?, ?, ?, datetime('now'))", (url, content, checksum))
            conn.commit()
        except Error as e:
            print(f"Error saving page: {e}")
        finally:
            conn.close()
    else:
        print("Error! Cannot create the database connection.")

def get_page_update_frequency(url):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM pages WHERE url = ? AND last_updated > datetime('now', '-7 days')", (url,))
            update_count = c.fetchone()[0]
            return update_count
        except Error as e:
            print(f"Error getting page update frequency: {e}")
        finally:
            conn.close()
    else:
        print("Error! Cannot create the database connection.")
    return 0

def prioritize_pages(urls):
    return sorted(urls, key=get_page_update_frequency, reverse=True)

def save_scrape_progress(url):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO scrape_progress VALUES (?, datetime('now'))", (url,))
            conn.commit()
        except Error as e:
            print(f"Error saving scrape progress: {e}")
        finally:
            conn.close()
    else:
        print("Error! Cannot create the database connection.")

def get_last_scraped_url():
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("SELECT url FROM scrape_progress ORDER BY last_scraped DESC LIMIT 1")
            result = c.fetchone()
            return result[0] if result else None
        except Error as e:
            print(f"Error getting last scraped URL: {e}")
        finally:
            conn.close()
    else:
        print("Error! Cannot create the database connection.")
    return None

def resume_scrape(start_url):
    last_url = get_last_scraped_url()
    if last_url:
        # Start scraping from the last successfully scraped URL
        start_scraping_from(last_url)
    else:
        # Start from the beginning
        start_scraping_from(start_url)

def save_link_integrity(result):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute('''INSERT OR REPLACE INTO link_integrity
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (result['url'], result.get('status_code'),
                       result.get('is_redirect'), result.get('final_url'),
                       result.get('content_type'), result.get('is_internal'),
                       result.get('anchor_exists')))
            conn.commit()
        except Error as e:
            print(f"Error saving link integrity: {e}")
        finally:
            conn.close()
    else:
        print("Error! Cannot create the database connection.")

def load_checksum(url):
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            c.execute("SELECT checksum FROM pages WHERE url = ?", (url,))
            result = c.fetchone()
            return result[0] if result else None
        except Error as e:
            print(f"Error loading checksum: {e}")
        finally:
            conn.close()
    return None

def start_scraping_from(url, doc_name, version, initial_delay=1, max_workers=5):
    logging.info(f"Starting scrape from URL: {url}")
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
            priority = calculate_priority(canonical_url, hash_manager, doc_name, version)
            queue.put((priority, canonical_url))
        except requests.RequestException as e:
            logging.error(f"Error fetching start URL: {e}")
            return

        scrape_pages_concurrently(queue, doc_name, version, rate_limiter, hash_manager, visited, base_domain, start_path, link_integrity_results, max_workers)
    except Exception as e:
        logging.error(f"Unexpected error in start_scraping_from: {e}")
        raise

def test_start_scraping_from():
    test_cases = [
        ("https://example.com", "Example", "1.0"),
        ("https://example.com/docs/", "Example", "2.0"),
        ("https://example.com/blog/article1", "ExampleBlog", "1.0"),
        ("https://subdomain.example.com", "SubExample", "1.0"),
    ]

    for url, doc_name, version in test_cases:
        print(f"Testing start_scraping_from with URL: {url}")
        start_scraping_from(url, doc_name, version)
        print("Test completed.")

if __name__ == "__main__":
    test_start_scraping_from()
