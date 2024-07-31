from dotenv import load_dotenv
import os

load_dotenv()

BRIGHT_DATA_USERNAME = os.environ.get('BRIGHT_DATA_USERNAME', 'brd-customer-hl_a2aba22a-zone-residential_proxy2')
BRIGHT_DATA_PASSWORD = os.environ.get('BRIGHT_DATA_PASSWORD', '')
BRIGHT_DATA_HOST = os.environ.get('BRIGHT_DATA_HOST', 'brd.superproxy.io')
BRIGHT_DATA_PORT = os.environ.get('BRIGHT_DATA_PORT', '22225')

def get_proxy_url():
    return f"http://{BRIGHT_DATA_USERNAME}:{BRIGHT_DATA_PASSWORD}@{BRIGHT_DATA_HOST}:{BRIGHT_DATA_PORT}"
