# ./00_html_content_collector/rate_limiter.py
import time
from statistics import mean
from custom_exceptions import RateLimitError
from logger import setup_logging, log_error, log_info, log_debug, log_warning

# Initialize loggers
loggers = setup_logging(output_dir='logs', doc_name='rate_limiter', version='v1')

class DynamicRateLimiter:
    def __init__(self, initial_delay=1, min_delay=0.5, max_delay=5, backoff_factor=1.5):
        self.current_delay = initial_delay
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.response_times = []

    def wait(self):
        log_debug(loggers, f"Waiting for {self.current_delay} seconds")
        time.sleep(self.current_delay)

    def update(self, response_time):
        self.response_times.append(response_time)
        if len(self.response_times) > 10:
            self.response_times.pop(0)

        avg_response_time = mean(self.response_times)
        log_debug(loggers, f"Average response time: {avg_response_time:.2f} seconds")

        if avg_response_time > 1:  # If average response time is over 1 second
            self.increase_delay()
        elif avg_response_time < 0.5 and self.current_delay > self.min_delay:
            self.decrease_delay()

    def increase_delay(self):
        old_delay = self.current_delay
        self.current_delay = min(self.current_delay * self.backoff_factor, self.max_delay)
        log_info(loggers, f"Increasing delay from {old_delay:.2f}s to {self.current_delay:.2f}s")

    def decrease_delay(self):
        old_delay = self.current_delay
        self.current_delay = max(self.current_delay / self.backoff_factor, self.min_delay)
        log_info(loggers, f"Decreasing delay from {old_delay:.2f}s to {self.current_delay:.2f}s")

    def backoff(self):
        old_delay = self.current_delay
        self.current_delay = min(self.current_delay * self.backoff_factor * 2, self.max_delay)
        log_warning(loggers, f"Backing off: increasing delay from {old_delay:.2f}s to {self.current_delay:.2f}s")

    def check_rate_limit(self, response):
        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                retry_after = int(retry_after)
                log_warning(loggers, f"Rate limit hit. Retry-After: {retry_after} seconds")
                raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after} seconds.",
                                     url=response.url,
                                     retry_after=retry_after)
            else:
                log_warning(loggers, "Rate limit hit. No Retry-After header. Using backoff.")
                self.backoff()
                raise RateLimitError("Rate limit exceeded. Using exponential backoff.",
                                     url=response.url)
