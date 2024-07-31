# config.py
import json
import os

def load_manifest():
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manifest_path = os.path.join(parent_dir, 'core_manifest.json')
    try:
        with open(manifest_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"core_manifest.json not found in {parent_dir}")


MANIFEST = load_manifest()

# Add any project-specific configurations here
PROJECT_NAME = "00_html_content_collector"  # or "01_clean_html" for the other project
OUTPUT_DIR = os.path.expanduser('~/tradeInsightDataSet/raw/docs')
