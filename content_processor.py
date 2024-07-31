from bs4 import BeautifulSoup
import extruct
import logging
import bleach
from dateutil import parser
from w3lib.html import get_base_url
from scraper import normalize_html_structure, normalize_urls, normalize_character_encoding, basic_content_cleaning, normalize_whitespace, detect_language

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
