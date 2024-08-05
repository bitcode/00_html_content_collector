# ./00_html_content_collector/utils.py
from urllib.parse import urlparse, urlunparse, urlencode, urldefrag, unquote, quote, parse_qsl
import idna
import requests
import os
import re
import hashlib
import random
import logging
from custom_exceptions import NetworkError, ParsingError

logger = logging.getLogger(__name__)

def normalize_url(url):
    try:
        if url.startswith('//'):
            url = 'http:' + url

        url = expand_shortened_url(url)

        url, _ = urldefrag(url)

        parsed = urlparse(url)

        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        try:
            netloc = netloc.encode('idna').decode('ascii')
        except idna.IDNAError:
            logger.warning(f"Failed to encode IDN: {netloc}")

        if netloc.startswith('www.'):
            netloc = 'www.' + netloc.replace('www.', '')
        elif netloc.startswith('www1.') or netloc.startswith('www2.'):
            netloc = 'www.' + netloc[5:]

        if (scheme == 'http' and parsed.port == 80) or (scheme == 'https' and parsed.port == 443):
            netloc = parsed.hostname

        path = parsed.path

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

        path = re.sub(r'//+', '/', path)

        if path:
            _, ext = os.path.splitext(path)
            if not ext:
                path = path.rstrip('/') + '/'
            else:
                path = path.rstrip('/')
        else:
            path = '/'

        path = unquote(path)
        path = quote(path, safe='/:@&=+$,')

        query = parsed.query
        if query:
            query_params = parse_qsl(query)
            query_params = sorted((k, v) for k, v in query_params if v and not is_session_id(k))
            query = urlencode(query_params)

        normalized = urlunparse((
            scheme,
            netloc,
            path,
            parsed.params,
            query,
            ''
        ))

        return normalized
    except Exception as e:
        logger.error(f"Error normalizing URL {url}: {str(e)}")
        raise ParsingError(f"Failed to normalize URL: {str(e)}", url=url)

def expand_shortened_url(url):
    shortener_domains = ['bit.ly', 'tinyurl.com', 't.co', 'goo.gl']
    parsed = urlparse(url)
    if parsed.netloc in shortener_domains:
        try:
            response = requests.head(url, allow_redirects=True, timeout=5)
            return response.url
        except requests.RequestException as e:
            logger.warning(f"Failed to expand shortened URL {url}: {str(e)}")
            raise NetworkError(f"Failed to expand shortened URL: {str(e)}", url=url)
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
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    return headers
