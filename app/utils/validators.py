import re
from typing import List, Optional, Tuple
from urllib.parse import urlparse, urljoin
import aiohttp


class URLValidator:
    @staticmethod
    def is_valid_url(url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    @staticmethod
    def normalize_url(url: str) -> str:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        parsed = urlparse(url)
        if not parsed.scheme:
            parsed = parsed._replace(scheme='https')
        
        return parsed.geturl().rstrip('/')
    
    @staticmethod
    def get_domain(url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc.lower()


class EmailPhoneExtractor:
    EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_REGEX = re.compile(
        r'(\+?\d{1,3}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}'
    )
    
    @classmethod
    def extract_emails(cls, text: str) -> List[str]:
        if not text:
            return []
        emails = cls.EMAIL_REGEX.findall(text)
        return list(set(email.lower() for email in emails if cls._is_valid_email(email)))
    
    @classmethod
    def extract_phone_numbers(cls, text: str) -> List[str]:
        if not text:
            return []
        phones = cls.PHONE_REGEX.findall(text)
        cleaned_phones = []
        for phone in phones:
            cleaned = re.sub(r'[^\d+]', '', phone)
            if len(cleaned) >= 10 and len(cleaned) <= 15:
                cleaned_phones.append(phone)
        return list(set(cleaned_phones))
    
    @staticmethod
    def _is_valid_email(email: str) -> bool:
        invalid_domains = ['example.com', 'test.com', 'demo.com', 'yourstore.com']
        domain = email.split('@')[-1].lower()
        return domain not in invalid_domains and not email.endswith('.png') and not email.endswith('.jpg')


class ShopifyDetector:
    SHOPIFY_INDICATORS = [
        'cdn.shopify.com',
        'myshopify.com',
        'Shopify.theme',
        'shopify_features',
        '/cart/add.js',
        '/cart.js',
        'window.Shopify',
        'ShopifyAnalytics',
        'shopify-section',
        'powered by shopify',
        '/products.json',
        'shopify-payment'
    ]
    
    @classmethod
    async def is_shopify_store(cls, url: str, html_content: Optional[str] = None) -> bool:
        if html_content:
            html_lower = html_content.lower()
            for indicator in cls.SHOPIFY_INDICATORS:
                if indicator.lower() in html_lower:
                    return True
        
        try:
            normalized_url = URLValidator.normalize_url(url)
            products_json_url = urljoin(normalized_url, '/products.json')
            
            async with aiohttp.ClientSession() as session:
                async with session.get(products_json_url, timeout=5) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                            return 'products' in data
                        except:
                            pass
        except:
            pass
        
        return False
    
    @classmethod
    def extract_shopify_data_from_html(cls, html: str) -> dict:
        data = {}
        
        currency_match = re.search(r'"currency":"([A-Z]{3})"', html)
        if currency_match:
            data['currency'] = currency_match.group(1)
        
        country_match = re.search(r'"country":"([A-Z]{2})"', html)
        if country_match:
            data['country'] = country_match.group(1)
        
        shop_name_match = re.search(r'"shop_name":"([^"]+)"', html)
        if shop_name_match:
            data['shop_name'] = shop_name_match.group(1)
        
        return data


class SocialMediaExtractor:
    SOCIAL_PLATFORMS = {
        'facebook.com': 'facebook',
        'instagram.com': 'instagram',
        'twitter.com': 'twitter',
        'x.com': 'twitter',
        'youtube.com': 'youtube',
        'tiktok.com': 'tiktok',
        'pinterest.com': 'pinterest',
        'linkedin.com': 'linkedin',
        'snapchat.com': 'snapchat'
    }
    
    @classmethod
    def extract_social_links(cls, html: str) -> List[Tuple[str, str]]:
        social_links = []
        link_pattern = re.compile(r'href=[\'"]?([^\'" >]+)', re.IGNORECASE)
        
        for match in link_pattern.finditer(html):
            url = match.group(1)
            for domain, platform in cls.SOCIAL_PLATFORMS.items():
                if domain in url:
                    social_links.append((platform, url))
                    break
        
        return list(set(social_links))
    
    @classmethod
    def extract_handle_from_url(cls, url: str) -> Optional[str]:
        patterns = [
            r'(?:facebook\.com|instagram\.com|twitter\.com|x\.com|tiktok\.com)/(@?[\w\-\.]+)',
            r'youtube\.com/(?:c|channel|user)/(@?[\w\-\.]+)',
            r'pinterest\.com/(@?[\w\-\.]+)',
            r'linkedin\.com/(?:company|in)/(@?[\w\-\.]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                handle = match.group(1)
                return handle.lstrip('@')
        
        return None