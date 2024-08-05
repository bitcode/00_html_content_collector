# ./00_html_content_collector/custom_exceptions.py

class ScraperError(Exception):
    """Base class for scraper exceptions."""

    def __init__(self, message, url=None):
        self.message = message
        self.url = url
        super().__init__(self.message)

    def log_message(self):
        return f"{self.__class__.__name__}: {self.message}" + (f" (URL: {self.url})" if self.url else "")

class NetworkError(ScraperError):
    """Raised when a network operation fails."""

    def __init__(self, message, url=None, status_code=None, original_error=None):
        super().__init__(message, url)
        self.status_code = status_code
        self.original_error = original_error

    def log_message(self):
        base_message = super().log_message()
        if self.status_code:
            base_message += f" (Status Code: {self.status_code})"
        if self.original_error:
            base_message += f" (Original Error: {str(self.original_error)})"
        return base_message

class ConnectionError(NetworkError):
    """Raised when a connection cannot be established."""

    def __init__(self, message, url=None, original_error=None):
        super().__init__(message, url, original_error=original_error)

    def log_message(self):
        return f"ConnectionError: {super().log_message()}"

class TimeoutError(NetworkError):
    """Raised when a network operation times out."""

    def __init__(self, message, url=None, timeout=None, original_error=None):
        super().__init__(message, url, original_error=original_error)
        self.timeout = timeout

    def log_message(self):
        base_message = f"TimeoutError: {super().log_message()}"
        if self.timeout:
            base_message += f" (Timeout: {self.timeout} seconds)"
        return base_message

class ParsingError(ScraperError):
    """Raised when parsing of content fails."""

    def __init__(self, message, url=None, parser=None, original_error=None):
        super().__init__(message, url)
        self.parser = parser
        self.original_error = original_error

    def log_message(self):
        base_message = f"ParsingError: {super().log_message()}"
        if self.parser:
            base_message += f" (Parser: {self.parser})"
        if self.original_error:
            base_message += f" (Original Error: {str(self.original_error)})"
        return base_message

class DatabaseError(ScraperError):
    """Raised when a database operation fails."""

    def __init__(self, message, operation=None, original_error=None):
        super().__init__(message)
        self.operation = operation
        self.original_error = original_error

    def log_message(self):
        base_message = f"DatabaseError: {super().log_message()}"
        if self.operation:
            base_message += f" (Operation: {self.operation})"
        if self.original_error:
            base_message += f" (Original Error: {str(self.original_error)})"
        return base_message

class ContentChangedError(ScraperError):
    """Raised when content has changed unexpectedly during scraping."""

    def __init__(self, message, url=None, old_checksum=None, new_checksum=None):
        super().__init__(message, url)
        self.old_checksum = old_checksum
        self.new_checksum = new_checksum

    def log_message(self):
        base_message = f"ContentChangedError: {super().log_message()}"
        if self.old_checksum and self.new_checksum:
            base_message += f" (Old Checksum: {self.old_checksum}, New Checksum: {self.new_checksum})"
        return base_message

class CircuitBreakerError(ScraperError):
    """Raised when the circuit breaker prevents an operation."""

    def __init__(self, message, url=None, failure_count=None, reset_timeout=None):
        super().__init__(message, url)
        self.failure_count = failure_count
        self.reset_timeout = reset_timeout

    def log_message(self):
        base_message = f"CircuitBreakerError: {super().log_message()}"
        if self.failure_count is not None:
            base_message += f" (Failure Count: {self.failure_count})"
        if self.reset_timeout is not None:
            base_message += f" (Reset Timeout: {self.reset_timeout} seconds)"
        return base_message

class LanguageDetectionError(ScraperError):
    """Raised when language detection fails or returns unexpected results."""

    def __init__(self, message, url=None, detected_language=None):
        super().__init__(message, url)
        self.detected_language = detected_language

    def log_message(self):
        return super().log_message() + (f" (Detected Language: {self.detected_language})" if self.detected_language else "")

class DuplicateContentError(ScraperError):
    """Raised when duplicate content is detected."""

    def __init__(self, message, url=None, duplicate_url=None):
        super().__init__(message, url)
        self.duplicate_url = duplicate_url

    def log_message(self):
        return super().log_message() + (f" (Duplicate URL: {self.duplicate_url})" if self.duplicate_url else "")

class MetadataExtractionError(ScraperError):
    """Raised when metadata extraction fails or is incomplete."""

    def __init__(self, message, url=None, partial_metadata=None):
        super().__init__(message, url)
        self.partial_metadata = partial_metadata

    def log_message(self):
        metadata_str = ", ".join(f"{k}: {v}" for k, v in self.partial_metadata.items()) if self.partial_metadata else "None"
        return super().log_message() + f" (Partial Metadata: {metadata_str})"

class RateLimitError(NetworkError):
    """Raised when the scraper hits a rate limit."""

    def __init__(self, message, url=None, retry_after=None):
        super().__init__(message, url)
        self.retry_after = retry_after

    def log_message(self):
        return super().log_message() + (f" (Retry After: {self.retry_after} seconds)" if self.retry_after else "")
