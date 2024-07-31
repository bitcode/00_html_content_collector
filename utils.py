from urllib.parse import urlparse, urlunparse, urlencode, urldefrag, unquote, quote, parse_qsl
import idna
import requests
import os
import re
import hashlib
import random
import logging


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


def calculate_checksum(content):
    return hashlib.md5(content.encode()).hexdigest()


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
