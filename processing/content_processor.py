# ./00_html_content_collector/content_processor.py
from bs4 import BeautifulSoup
import extruct
from dateutil import parser
from w3lib.html import get_base_url
import bleach
from datetime import datetime
from scraper import (
    normalize_html_structure, normalize_urls, normalize_character_encoding,
    basic_content_cleaning, normalize_whitespace, detect_language, extract_title,
    preserve_latex, extract_and_convert_svgs, extract_and_convert_iframe_svgs,
    preserve_katex, preserve_mathjax
)
from custom_exceptions import ParsingError, MetadataExtractionError, LanguageDetectionError
from logger import setup_logging, log_error, log_info

# Initialize loggers
loggers = setup_logging(output_dir='logs', doc_name='content_processor', version='v1')

def clean_and_normalize_content(content, url):
    try:
        soup = BeautifulSoup(content, 'html.parser')

        soup = normalize_html_structure(soup)
        soup = normalize_character_encoding(soup)
        soup = normalize_urls(soup, url)
        soup = basic_content_cleaning(soup)

        normalized_text = normalize_whitespace(soup.get_text())

        metadata = extract_and_normalize_metadata(soup)
        try:
            metadata['language'] = detect_language(normalized_text)
        except Exception as e:
            raise LanguageDetectionError(f"Failed to detect language: {str(e)}", url=url)

        log_info(loggers, f"Successfully cleaned and normalized content for URL: {url}")
        return str(soup), metadata
    except Exception as e:
        log_error(loggers, ParsingError(f"Failed to clean and normalize content: {str(e)}", url=url))
        raise

def extract_and_normalize_metadata(soup):
    metadata = {}
    try:
        for meta in soup.find_all('meta'):
            if 'name' in meta.attrs and 'content' in meta.attrs:
                if meta['name'] in ['date', 'pubdate', 'lastmod', 'modified']:
                    try:
                        metadata[meta['name']] = parser.parse(meta['content']).isoformat()
                    except ValueError:
                        log_error(loggers, MetadataExtractionError(f"Unable to parse date: {meta['content']}", partial_metadata=metadata))

        authors = soup.find_all('meta', attrs={'name': 'author'})
        if authors:
            metadata['authors'] = [author['content'].strip() for author in authors]

        log_info(loggers, "Successfully extracted and normalized metadata")
        return metadata
    except Exception as e:
        log_error(loggers, MetadataExtractionError(f"Failed to extract and normalize metadata: {str(e)}", partial_metadata=metadata))
        raise

def extract_metadata(soup, url, html_content):
    try:
        metadata = {
            'url': url,
            'extraction_date': datetime.now().isoformat(),
            'title': extract_title(soup),
            'description': None,
            'keywords': None,
            'last_modified': None,
            'structured_data': None,
        }

        desc_tag = soup.find('meta', attrs={'name': 'description'})
        if desc_tag:
            metadata['description'] = desc_tag.get('content')

        keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_tag:
            metadata['keywords'] = keywords_tag.get('content')

        last_modified_tag = soup.find('meta', attrs={'name': 'last-modified'})
        if last_modified_tag:
            metadata['last_modified'] = last_modified_tag.get('content')

        og_tags = soup.find_all('meta', property=lambda x: x and x.startswith('og:'))
        metadata['og'] = {tag.get('property')[3:]: tag.get('content') for tag in og_tags}

        base_url = get_base_url(html_content, url)
        structured_data = extruct.extract(
            html_content,
            base_url=base_url,
            syntaxes=['json-ld', 'microdata', 'rdfa']
        )

        cleaned_structured_data = {key: value for key, value in structured_data.items() if value}
        metadata['structured_data'] = cleaned_structured_data

        if last_modified_tag:
            try:
                parsed_date = parser.parse(last_modified_tag.get('content'))
                metadata['last_modified'] = parsed_date.isoformat()
            except ValueError:
                log_error(loggers, MetadataExtractionError(f"Unable to parse last modified date: {last_modified_tag.get('content')}", url=url, partial_metadata=metadata))

        log_info(loggers, f"Successfully extracted metadata for URL: {url}")
        return metadata
    except Exception as e:
        log_error(loggers, MetadataExtractionError(f"Failed to extract metadata: {str(e)}", url=url, partial_metadata=metadata))
        raise

def process_html_content(soup, url, directory):
    try:
        preserve_latex(soup)
        preserve_math_content(soup)
        preserve_code_blocks(soup)
        extract_and_convert_svgs(soup, directory)
        extract_and_convert_iframe_svgs(soup, directory, url)
        log_info(loggers, f"Successfully processed HTML content for URL: {url}")
    except Exception as e:
        log_error(loggers, ParsingError(f"Failed to process HTML content: {str(e)}", url=url))
        raise

def preserve_math_content(soup):
    for math_element in soup.find_all(['script', 'span', 'div'], class_=['math-inline', 'math-block', 'MathJax', 'katex-inline', 'katex-block']):
        math_element.string = preserve_mathjax(str(math_element))
        math_element.string = preserve_katex(str(math_element))

def preserve_code_blocks(soup):
    for code_block in soup.find_all(['pre', 'code']):
        code_block.string = bleach.clean(str(code_block), tags=['pre', 'code'], attributes={'class': []})

# Note: Functions like extract_title, preserve_latex, extract_and_convert_svgs,
# extract_and_convert_iframe_svgs, preserve_mathjax, and preserve_katex should be
# updated similarly with proper error handling and logging.


if __name__ == "__main__":
    # Example usage
    try:
        sample_content = "<html><body><p>Sample content</p></body></html>"
        sample_url = "https://example.com"
        cleaned_content, metadata = clean_and_normalize_content(sample_content, sample_url)
        print("Cleaned content:", cleaned_content)
        print("Metadata:", metadata)
    except Exception as e:
        log_error(loggers, e)
