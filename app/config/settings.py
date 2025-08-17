from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from functools import lru_cache
import os


class AppSettings(BaseSettings):
    """Application settings."""
    
    app_name: str = Field(default="Shopify Store Insights Fetcher", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"  # Ignore extra fields from environment
    }


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    database_url: str = Field(
        default="mysql+aiomysql://user:password@localhost:3306/shopify_insights",
        env="DATABASE_URL"
    )
    pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    echo_sql: bool = Field(default=False, env="DB_ECHO_SQL")
    
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if v.startswith("mysql://"):
            return v.replace("mysql://", "mysql+aiomysql://")
        return v
    
    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


class RedisSettings(BaseSettings):
    """Redis configuration settings."""
    
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    default_ttl: int = Field(default=3600, env="REDIS_DEFAULT_TTL")
    max_connections: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")
    
    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


class ScrapingSettings(BaseSettings):
    """Web scraping configuration settings."""
    
    user_agent: str = Field(
        default="ShopifyInsightsFetcher/1.0",
        env="USER_AGENT"
    )
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    concurrent_requests: int = Field(default=10, env="CONCURRENT_REQUESTS")
    headless_browser: bool = Field(default=True, env="HEADLESS_BROWSER")
    
    # Limits
    max_products_to_fetch: int = Field(default=100, env="MAX_PRODUCTS")
    max_hero_products: int = Field(default=5, env="MAX_HERO_PRODUCTS")
    max_faqs: int = Field(default=20, env="MAX_FAQS")
    max_social_handles: int = Field(default=10, env="MAX_SOCIAL_HANDLES")
    max_important_links: int = Field(default=15, env="MAX_IMPORTANT_LINKS")
    
    # Character limits
    max_policy_length: int = Field(default=5000, env="MAX_POLICY_LENGTH")
    max_brand_context_length: int = Field(default=2000, env="MAX_BRAND_CONTEXT_LENGTH")
    max_faq_answer_length: int = Field(default=500, env="MAX_FAQ_ANSWER_LENGTH")
    
    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


class LLMSettings(BaseSettings):
    """LLM service configuration settings."""
    
    # API Keys
    gemini_api_key: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    
    # Model settings
    gemini_model: str = Field(default="gemini-pro", env="GEMINI_MODEL")
    openai_model: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL")
    anthropic_model: str = Field(default="claude-3-haiku-20240307", env="ANTHROPIC_MODEL")
    
    # Token and temperature settings
    gemini_max_tokens: int = Field(default=1000, env="GEMINI_MAX_TOKENS")
    gemini_temperature: float = Field(default=0.3, env="GEMINI_TEMPERATURE")
    openai_max_tokens: int = Field(default=1000, env="OPENAI_MAX_TOKENS")
    openai_temperature: float = Field(default=0.3, env="OPENAI_TEMPERATURE")
    anthropic_max_tokens: int = Field(default=1000, env="ANTHROPIC_MAX_TOKENS")
    
    # General LLM settings
    use_llm_for_extraction: bool = Field(default=True, env="USE_LLM_FOR_EXTRACTION")
    llm_provider: str = Field(default="gemini", env="LLM_PROVIDER")  # gemini, openai, anthropic, none
    llm_fallback_enabled: bool = Field(default=True, env="LLM_FALLBACK_ENABLED")
    
    @property
    def is_enabled(self) -> bool:
        return bool(self.use_llm_for_extraction and (self.gemini_api_key or self.openai_api_key or self.anthropic_api_key))
    
    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


class RateLimitSettings(BaseSettings):
    """Rate limiting configuration settings."""
    
    requests_per_minute: int = Field(default=60, env="REQUESTS_PER_MINUTE")
    requests_per_hour: int = Field(default=1000, env="REQUESTS_PER_HOUR")
    burst_size: int = Field(default=10, env="BURST_SIZE")
    
    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


class ShopifySettings(BaseSettings):
    """Shopify-specific configuration settings."""
    
    # Shopify endpoints
    products_endpoint: str = Field(default="/products.json", env="SHOPIFY_PRODUCTS_ENDPOINT")
    
    # Policy URLs
    policy_paths: List[str] = Field(
        default=[
            "/pages/privacy-policy",
            "/policies/privacy-policy",
            "/privacy-policy",
            "/privacy"
        ]
    )
    
    return_policy_paths: List[str] = Field(
        default=[
            "/pages/refund-policy",
            "/policies/refund-policy",
            "/pages/return-policy",
            "/pages/returns",
            "/refund-policy",
            "/returns"
        ]
    )
    
    shipping_policy_paths: List[str] = Field(
        default=[
            "/pages/shipping-policy",
            "/policies/shipping-policy",
            "/shipping-policy",
            "/shipping"
        ]
    )
    
    terms_paths: List[str] = Field(
        default=[
            "/pages/terms-of-service",
            "/policies/terms-of-service",
            "/terms-of-service",
            "/terms"
        ]
    )
    
    faq_paths: List[str] = Field(
        default=[
            "/pages/faq",
            "/pages/faqs",
            "/pages/help",
            "/pages/help-center",
            "/pages/support",
            "/faq",
            "/help"
        ]
    )
    
    about_paths: List[str] = Field(
        default=[
            "/pages/about",
            "/pages/about-us",
            "/pages/our-story",
            "/about",
            "/our-story"
        ]
    )
    
    contact_paths: List[str] = Field(
        default=[
            "/pages/contact",
            "/pages/contact-us",
            "/contact"
        ]
    )
    
    # Shopify detection indicators
    shopify_indicators: List[str] = Field(
        default=[
            "cdn.shopify.com",
            "myshopify.com",
            "Shopify.theme",
            "shopify_features",
            "/cart/add.js",
            "/cart.js",
            "window.Shopify",
            "ShopifyAnalytics",
            "shopify-section",
            "powered by shopify",
            "/products.json",
            "shopify-payment"
        ]
    )
    
    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


class Settings(BaseSettings):
    """Main settings class that combines all settings."""
    
    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    scraping: ScrapingSettings = Field(default_factory=ScrapingSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    shopify: ShopifySettings = Field(default_factory=ShopifySettings)
    
    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Export individual settings for convenience
@lru_cache()
def get_app_settings() -> AppSettings:
    return AppSettings()


@lru_cache()
def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


@lru_cache()
def get_redis_settings() -> RedisSettings:
    return RedisSettings()


@lru_cache()
def get_scraping_settings() -> ScrapingSettings:
    return ScrapingSettings()


@lru_cache()
def get_llm_settings() -> LLMSettings:
    return LLMSettings()


@lru_cache()
def get_rate_limit_settings() -> RateLimitSettings:
    return RateLimitSettings()


@lru_cache()
def get_shopify_settings() -> ShopifySettings:
    return ShopifySettings()