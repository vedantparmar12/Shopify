from typing import Optional, Dict, Any


class InsightsAPIException(Exception):
    def __init__(self, message: str, status_code: int, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class WebsiteNotFoundException(InsightsAPIException):
    def __init__(self, url: str):
        super().__init__(
            message=f"Website not found: {url}",
            status_code=401,
            details={"url": url}
        )


class InvalidURLException(InsightsAPIException):
    def __init__(self, url: str):
        super().__init__(
            message=f"Invalid URL format: {url}",
            status_code=422,
            details={"url": url}
        )


class NotShopifyStoreException(InsightsAPIException):
    def __init__(self, url: str):
        super().__init__(
            message=f"The website is not a Shopify store: {url}",
            status_code=400,
            details={"url": url}
        )


class ScrapingException(InsightsAPIException):
    def __init__(self, url: str, error: str):
        super().__init__(
            message=f"Failed to scrape website: {error}",
            status_code=500,
            details={"url": url, "error": error}
        )


class RateLimitException(InsightsAPIException):
    def __init__(self, retry_after: Optional[int] = None):
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            status_code=429,
            details={"retry_after": retry_after}
        )


class DatabaseException(InsightsAPIException):
    def __init__(self, error: str):
        super().__init__(
            message=f"Database operation failed: {error}",
            status_code=500,
            details={"error": error}
        )


class LLMServiceException(InsightsAPIException):
    def __init__(self, error: str):
        super().__init__(
            message=f"LLM service error: {error}",
            status_code=500,
            details={"error": error}
        )