import time
from statistics import mean

class DynamicRateLimiter:
    def __init__(self, initial_delay=1, min_delay=0.5, max_delay=5, backoff_factor=1.5):
        self.current_delay = initial_delay
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.response_times = []

    def wait(self):
        time.sleep(self.current_delay)

    def update(self, response_time):
        self.response_times.append(response_time)
        if len(self.response_times) > 10:
            self.response_times.pop(0)

        avg_response_time = mean(self.response_times)

        if avg_response_time > 1:  # If average response time is over 1 second
            self.increase_delay()
        elif avg_response_time < 0.5 and self.current_delay > self.min_delay:
            self.decrease_delay()

    def increase_delay(self):
        self.current_delay = min(self.current_delay * self.backoff_factor, self.max_delay)

    def decrease_delay(self):
        self.current_delay = max(self.current_delay / self.backoff_factor, self.min_delay)

    def backoff(self):
        self.current_delay = min(self.current_delay * self.backoff_factor * 2, self.max_delay)
