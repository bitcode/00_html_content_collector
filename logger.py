import os
import logging
from custom_exceptions import (
    ScraperError, NetworkError, ParsingError, DatabaseError,
    LanguageDetectionError, DuplicateContentError, MetadataExtractionError
)

def setup_logging(output_dir, doc_name, version):
    base_logger = logging.getLogger(f'scraper.{doc_name}.{version}')
    base_logger.setLevel(logging.DEBUG)

    log_dir = os.path.join(output_dir, 'logs', doc_name, version)
    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create separate loggers for each error category
    loggers = {}
    categories = ['network', 'parsing', 'database', 'language_detection', 'duplicate_content', 'metadata_extraction', 'general']

    for category in categories:
        logger = logging.getLogger(f'scraper.{doc_name}.{version}.{category}')
        logger.setLevel(logging.DEBUG)

        file_handler = logging.FileHandler(os.path.join(log_dir, f'{category}.log'))
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        loggers[category] = logger

    return loggers

def log_error(loggers, error):
    if isinstance(error, NetworkError):
        loggers['network'].error(f"Network Error: {str(error)}")
    elif isinstance(error, ParsingError):
        loggers['parsing'].error(f"Parsing Error: {str(error)}")
    elif isinstance(error, DatabaseError):
        loggers['database'].error(f"Database Error: {str(error)}")
    elif isinstance(error, LanguageDetectionError):
        loggers['language_detection'].error(f"Language Detection Error: {str(error)}")
    elif isinstance(error, DuplicateContentError):
        loggers['duplicate_content'].warning(f"Duplicate Content Detected: {str(error)}")
    elif isinstance(error, MetadataExtractionError):
        loggers['metadata_extraction'].error(f"Metadata Extraction Error: {str(error)}")
    elif isinstance(error, ScraperError):
        loggers['general'].error(f"Scraper Error: {str(error)}")
    else:
        loggers['general'].error(f"Unexpected Error: {str(error)}")

def log_info(loggers, message):
    loggers['general'].info(message)

