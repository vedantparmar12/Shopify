from enum import Enum
from typing import Dict, List


class ExtractionStatus(str, Enum):
    """Extraction status enum."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    PENDING = "pending"


class SocialPlatform(str, Enum):
    """Social media platforms."""
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    PINTEREST = "pinterest"
    LINKEDIN = "linkedin"
    SNAPCHAT = "snapchat"
    OTHER = "other"


class LinkCategory(str, Enum):
    """Important link categories."""
    SUPPORT = "support"
    TRACKING = "tracking"
    BLOG = "blog"
    ABOUT = "about"
    LEGAL = "legal"
    HELP = "help"
    ACCOUNT = "account"
    OTHER = "other"


class PolicyType(str, Enum):
    """Policy types."""
    PRIVACY = "privacy_policy"
    RETURN_REFUND = "return_refund_policy"
    SHIPPING = "shipping_policy"
    TERMS = "terms_of_service"


# Social media domain mapping
SOCIAL_DOMAIN_MAPPING: Dict[str, str] = {
    "facebook.com": SocialPlatform.FACEBOOK,
    "instagram.com": SocialPlatform.INSTAGRAM,
    "twitter.com": SocialPlatform.TWITTER,
    "x.com": SocialPlatform.TWITTER,
    "youtube.com": SocialPlatform.YOUTUBE,
    "tiktok.com": SocialPlatform.TIKTOK,
    "pinterest.com": SocialPlatform.PINTEREST,
    "linkedin.com": SocialPlatform.LINKEDIN,
    "snapchat.com": SocialPlatform.SNAPCHAT,
}

# Invalid email domains to filter out
INVALID_EMAIL_DOMAINS: List[str] = [
    "example.com",
    "test.com",
    "demo.com",
    "yourstore.com",
    "placeholder.com",
    "sample.com"
]

# Invalid email extensions to filter out
INVALID_EMAIL_EXTENSIONS: List[str] = [
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp"
]

# Link category keywords
LINK_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    LinkCategory.SUPPORT: ["support", "help", "customer-service", "assistance"],
    LinkCategory.TRACKING: ["track", "tracking", "order-status", "shipment"],
    LinkCategory.BLOG: ["blog", "news", "articles", "posts"],
    LinkCategory.ABOUT: ["about", "our-story", "who-we-are", "mission"],
    LinkCategory.LEGAL: ["legal", "terms", "privacy", "policy", "disclaimer"],
    LinkCategory.ACCOUNT: ["account", "login", "register", "my-account", "signin"],
}

# FAQ detection patterns
FAQ_PATTERNS: List[Dict[str, str]] = [
    {"container": "div.faq-item", "question": "h3", "answer": "div.answer"},
    {"container": "div.accordion-item", "question": "button", "answer": "div.accordion-content"},
    {"container": "details", "question": "summary", "answer": None},
    {"container": "div[class*='faq']", "question": "h3,h4", "answer": "p,div"},
]

# Question prefixes to detect
QUESTION_PREFIXES: List[str] = ["Q:", "Question:", "Q.", "FAQ:"]

# Answer prefixes to detect
ANSWER_PREFIXES: List[str] = ["A:", "Answer:", "A.", "Response:"]

# Hero product selectors
HERO_PRODUCT_SELECTORS: List[str] = [
    "section.featured-products",
    "div.hero-products",
    "section.hero-product",
    "div.featured-collection",
    "section[class*='featured']",
    "section[class*='hero']",
    "div[class*='featured-product']",
]

# Content selectors for policies and about pages
CONTENT_SELECTORS: List[str] = [
    "main",
    "article",
    "div.page-content",
    "div.policy-content",
    "div.content",
    "div.about-content",
    "section.content",
]

# Address selectors
ADDRESS_SELECTORS: List[str] = [
    "div[class*='address']",
    "address",
    "div[class*='location']",
    "p[class*='address']",
    "span[class*='address']",
]

# Phone number regex pattern
PHONE_REGEX_PATTERN: str = r"(\+?\d{1,3}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}"

# Email regex pattern
EMAIL_REGEX_PATTERN: str = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

# Minimum lengths for validation
MIN_POLICY_LENGTH: int = 100
MIN_BRAND_CONTEXT_LENGTH: int = 50
MIN_FAQ_QUESTION_LENGTH: int = 5
MIN_FAQ_ANSWER_LENGTH: int = 10
MIN_PHONE_LENGTH: int = 10
MAX_PHONE_LENGTH: int = 15

# HTTP status codes
HTTP_OK: int = 200
HTTP_BAD_REQUEST: int = 400
HTTP_UNAUTHORIZED: int = 401
HTTP_NOT_FOUND: int = 404
HTTP_UNPROCESSABLE_ENTITY: int = 422
HTTP_TOO_MANY_REQUESTS: int = 429
HTTP_INTERNAL_SERVER_ERROR: int = 500

# Cache keys
CACHE_KEY_PREFIX: str = "insights"
CACHE_RECENT_KEY: str = "recent_extractions"
CACHE_TAG_PREFIX: str = "tag"

# Database table names
TABLE_BRAND_INSIGHTS: str = "brand_insights"
TABLE_COMPETITOR_ANALYSIS: str = "competitor_analyses"
TABLE_EXTRACTION_LOG: str = "extraction_logs"

# Test Shopify stores
TEST_SHOPIFY_STORES: List[str] = [
    "https://memy.co.in",
    "https://hairoriginals.com",
    "https://colourpop.com",
    "https://fashionnova.com",
    "https://gymshark.com",
    "https://allbirds.com",
    "https://kith.com",
    "https://bulletproof.com",
    "https://gfuel.com",
    "https://stevemadden.com",
]