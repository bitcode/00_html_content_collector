import time
import requests
from requests.exceptions import RequestException
from scraper import get_proxy_url

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
