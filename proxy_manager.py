# ./00_html_content_collector/proxy_manager.py
import time
import requests
from requests.exceptions import RequestException
from scraper import get_proxy_url
from custom_exceptions import ConnectionError, NetworkError, ConfigurationError
from logger import setup_logging, log_error, log_info, log_warning, log_debug

# Initialize logging
loggers = setup_logging(output_dir='logs', doc_name='proxy_manager', version='v1')

class ProxyManager:
    def __init__(self, max_failures=3, health_check_interval=300):
        try:
            self.proxy_url = get_proxy_url()
            self.max_failures = max_failures
            self.health_check_interval = health_check_interval
            self.failure_count = 0
            self.last_health_check = 0
            self.proxy = {
                'http': self.proxy_url,
                'https': self.proxy_url
            }
            log_info(loggers, "ProxyManager initialized successfully")
        except Exception as e:
            log_error(loggers, f"Failed to initialize ProxyManager: {str(e)}")
            raise ConfigurationError(f"ProxyManager initialization failed: {str(e)}")

    def get_proxy(self):
        try:
            current_time = time.time()
            if current_time - self.last_health_check > self.health_check_interval:
                self.check_proxy_health()
            log_debug(loggers, f"Returning proxy: {self.proxy}")
            return self.proxy
        except Exception as e:
            log_error(loggers, f"Error in get_proxy: {str(e)}")
            raise NetworkError(f"Failed to get proxy: {str(e)}")

    def check_proxy_health(self):
        try:
            response = requests.get('https://httpbin.org/ip', proxies=self.proxy, timeout=10)
            response.raise_for_status()
            self.failure_count = 0
            self.last_health_check = time.time()
            log_info(loggers, f"Proxy health check passed. IP: {response.json()['origin']}")
        except RequestException as e:
            self.failure_count += 1
            log_warning(loggers, f"Proxy health check failed: {str(e)}")
            if self.failure_count >= self.max_failures:
                self.rotate_proxy()
                raise ConnectionError("Failed proxy health check. Rotating proxy.", url='https://httpbin.org/ip', original_error=e)
        except Exception as e:
            log_error(loggers, f"Unexpected error in proxy health check: {str(e)}")
            raise NetworkError(f"Unexpected error in proxy health check: {str(e)}")

    def rotate_proxy(self):
        try:
            # For Bright Data, rotation is automatic, so we just reset the failure count
            self.failure_count = 0
            log_info(loggers, "Proxy rotated (Bright Data handles rotation automatically)")
        except Exception as e:
            log_error(loggers, f"Error rotating proxy: {str(e)}")
            raise NetworkError(f"Failed to rotate proxy: {str(e)}")

    def handle_request_error(self, error):
        try:
            self.failure_count += 1
            log_warning(loggers, f"Proxy request failed: {str(error)}")
            if self.failure_count >= self.max_failures:
                self.rotate_proxy()
                raise NetworkError("Multiple proxy request failures. Rotating proxy.", original_error=error)
        except Exception as e:
            log_error(loggers, f"Error handling request failure: {str(e)}")
            raise NetworkError(f"Error handling request failure: {str(e)}", original_error=error)
