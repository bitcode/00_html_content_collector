# ./00_html_content_collector/config.py
import yaml
import os
import logging
from custom_exceptions import ConfigurationError

logger = logging.getLogger(__name__)

def load_manifest():
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manifest_path = os.path.join(parent_dir, 'core_manifest.yaml')
    try:
        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)
        logger.info("Successfully loaded core_manifest.yaml")
        return manifest
    except FileNotFoundError:
        error_msg = f"core_manifest.yaml not found in {parent_dir}"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)
    except yaml.YAMLError as e:
        error_msg = f"Error parsing core_manifest.yaml: {str(e)}"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error loading core_manifest.yaml: {str(e)}"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)


try:
    MANIFEST = load_manifest()
    logger.info("Manifest loaded successfully")
except ConfigurationError as e:
    logger.critical(f"Failed to load manifest: {str(e)}")
    raise

# Add any project-specific configurations here
PROJECT_NAME = MANIFEST.get('project_name', "00_html_content_collector")
OUTPUT_DIR = os.path.expanduser(MANIFEST.get('dataset_structure', {}).get('base_dir', '~/tradeInsightDataSet/raw/docs'))

# Validate crucial configuration
if not os.path.exists(OUTPUT_DIR):
    try:
        os.makedirs(OUTPUT_DIR)
        logger.info(f"Created OUTPUT_DIR: {OUTPUT_DIR}")
    except OSError as e:
        error_msg = f"Failed to create OUTPUT_DIR {OUTPUT_DIR}: {str(e)}"
        logger.critical(error_msg)
        raise ConfigurationError(error_msg)

# You can add more configuration validations here
def validate_config():
    if not MANIFEST:
        raise ConfigurationError("MANIFEST is empty or not properly loaded")
    if not PROJECT_NAME:
        raise ConfigurationError("PROJECT_NAME is not set")
    if not OUTPUT_DIR:
        raise ConfigurationError("OUTPUT_DIR is not set")
    # Add more validations as needed


try:
    validate_config()
    logger.info("Configuration validated successfully")
except ConfigurationError as e:
    logger.critical(f"Configuration validation failed: {str(e)}")
    raise

logger.info("Configuration loaded and validated successfully")
