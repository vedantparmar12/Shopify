"""Scrapy-based Shopify store scraper service for robust data extraction."""

import asyncio
import json
import re
import time
from typing import List, Dict, Optional, Any, Set
from datetime import datetime
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor
import scrapy
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from twisted.internet import asyncioreactor
from twisted.internet import reactor
import logging

from app.models.brand_insights import (
    BrandInsights, ProductInfo, SocialHandle, 
    FAQ, ContactInfo, ImportantLink
)
from app.utils.validators import (
    URLValidator, EmailPhoneExtractor, 
    ShopifyDetector, SocialMediaExtractor
)
from app.utils.exceptions import (
    WebsiteNotFoundException, NotShopifyStoreException, 
    ScrapingException
)
from app.config.settings import get_scraping_settings, get_shopify_settings
from app.config.constants import (
    HERO_PRODUCT_SELECTORS, FAQ_PATTERNS, CONTENT_SELECTORS,
    MIN_POLICY_LENGTH, MIN_BRAND_CONTEXT_LENGTH
)


class ShopifySpider(scrapy.Spider):
    """Scrapy spider for extracting Shopify store data."""
    
    name = 'shopify_spider'
    
    def __init__(self, start_url, insights_data=None, *args, **kwargs):
        super(ShopifySpider, self).__init__(*args, **kwargs)
        self.start_urls = [start_url]
        self.base_url = start_url
        self.insights_data = insights_data or {}
        self.visited_urls = set()
        
        # Configure settings
        self.scraping_settings = get_scraping_settings()
        self.shopify_settings = get_shopify_settings()
    
    def start_requests(self):
        """Generate initial requests."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        for url in self.start_urls:
            yield scrapy.Request(
                url=url, 
                callback=self.parse_homepage,
                headers=headers,
                meta={'dont_redirect': False, 'handle_httpstatus_list': [301, 302, 404]}
            )
    
    def parse_homepage(self, response):
        """Parse the main homepage."""
        if response.status == 404:
            self.insights_data['error'] = f"Website not found: {response.url}"
            return
        
        self.insights_data['homepage_content'] = response.text
        self.insights_data['website_url'] = response.url
        
        # Check if it's a Shopify store
        is_shopify = self._detect_shopify(response)
        self.insights_data['is_shopify'] = is_shopify
        
        if not is_shopify:
            self.insights_data['error'] = "Not a Shopify store"
            return
        
        # Extract basic data from homepage
        self._extract_homepage_data(response)
        
        # Get products.json
        products_url = urljoin(self.base_url, '/products.json')
        yield scrapy.Request(
            url=products_url,
            callback=self.parse_products_json,
            headers={'Accept': 'application/json'},
            meta={'dont_redirect': False}
        )
        
        # Request policy pages
        policy_urls = [
            '/pages/privacy-policy', '/pages/return-policy', '/pages/refund-policy',
            '/pages/shipping-policy', '/pages/terms-of-service', '/pages/terms-and-conditions',
            '/policies/privacy-policy', '/policies/return-policy', '/policies/refund-policy',
            '/policies/shipping-policy', '/policies/terms-of-service'
        ]
        
        for policy_path in policy_urls:
            full_url = urljoin(self.base_url, policy_path)
            yield scrapy.Request(
                url=full_url,
                callback=self.parse_policy_page,
                meta={'policy_type': self._get_policy_type(policy_path)},
                dont_filter=True,
                errback=self.handle_error
            )
        
        # Request FAQ and other pages
        other_pages = [
            '/pages/faq', '/pages/faqs', '/pages/help', '/faq', '/faqs',
            '/pages/about', '/pages/about-us', '/pages/our-story', '/about', '/about-us',
            '/pages/contact', '/pages/contact-us', '/contact', '/contact-us'
        ]
        
        for page_path in other_pages:
            full_url = urljoin(self.base_url, page_path)
            yield scrapy.Request(
                url=full_url,
                callback=self.parse_content_page,
                meta={'page_type': self._get_page_type(page_path)},
                dont_filter=True,
                errback=self.handle_error
            )
    
    def parse_products_json(self, response):
        """Parse products.json endpoint."""
        try:
            if response.status == 200:
                data = json.loads(response.text)
                products = data.get('products', [])
                self.insights_data['products_json'] = products[:100]  # Limit to 100 products
                self.logger.info(f"Found {len(products)} products in products.json")
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse products.json: {response.url}")
    
    def parse_policy_page(self, response):
        """Parse policy pages."""
        if response.status == 200:
            policy_type = response.meta.get('policy_type')
            if policy_type:
                content = self._extract_main_content(response)
                if content and len(content) > MIN_POLICY_LENGTH:
                    if 'policies' not in self.insights_data:
                        self.insights_data['policies'] = {}
                    self.insights_data['policies'][policy_type] = {
                        'content': content[:2000],  # Limit content length
                        'url': response.url
                    }
    
    def parse_content_page(self, response):
        """Parse FAQ, about, contact pages."""
        if response.status == 200:
            page_type = response.meta.get('page_type')
            content = self._extract_main_content(response)
            
            if page_type == 'faq':
                faqs = self._extract_faqs_from_response(response)
                if faqs:
                    self.insights_data['faqs'] = faqs
            elif page_type == 'about':
                if content and len(content) > MIN_BRAND_CONTEXT_LENGTH:
                    self.insights_data['brand_context'] = content[:1000]
            elif page_type == 'contact':
                contact_info = self._extract_contact_info(response)
                if contact_info:
                    self.insights_data['contact_info'] = contact_info
    
    def handle_error(self, failure):
        """Handle request errors."""
        self.logger.error(f"Request failed: {failure.request.url} - {failure.value}")
    
    def _detect_shopify(self, response):
        """Detect if the site is a Shopify store."""
        text = response.text.lower()
        
        # Check for Shopify indicators
        shopify_indicators = [
            'shopify', 'myshopify', 'cdn.shopify', 'shop.app',
            'shopify-section', 'shopify.theme', 'shopify analytics'
        ]
        
        return any(indicator in text for indicator in shopify_indicators)
    
    def _extract_homepage_data(self, response):
        """Extract data from homepage."""
        # Extract brand name
        brand_name = self._extract_brand_name(response)
        if brand_name:
            self.insights_data['brand_name'] = brand_name
        
        # Extract hero products
        hero_products = self._extract_hero_products(response)
        if hero_products:
            self.insights_data['hero_products'] = hero_products
        
        # Extract social handles
        social_handles = self._extract_social_handles(response)
        if social_handles:
            self.insights_data['social_handles'] = social_handles
        
        # Extract important links
        important_links = self._extract_important_links(response)
        if important_links:
            self.insights_data['important_links'] = important_links
    
    def _extract_brand_name(self, response):
        """Extract brand name from various sources."""
        # Try meta tags first
        og_title = response.css('meta[property="og:site_name"]::attr(content)').get()
        if og_title:
            return og_title.strip()
        
        # Try title tag
        title = response.css('title::text').get()
        if title:
            # Clean up title (remove common separators)
            for sep in ['|', '-', '·', '–', '—']:
                if sep in title:
                    return title.split(sep)[0].strip()
            return title.strip()
        
        # Try logo alt text
        logo_alt = response.css('img[class*="logo"]::attr(alt), img[id*="logo"]::attr(alt)').get()
        if logo_alt:
            return logo_alt.strip()
        
        # Fallback to domain name
        domain = urlparse(response.url).netloc.replace('www.', '')
        return domain.split('.')[0].capitalize()
    
    def _extract_hero_products(self, response):
        """Extract hero/featured products from homepage."""
        hero_products = []
        
        # Look for product links on the homepage
        product_links = response.css('a[href*="/products/"]')
        
        for link in product_links[:10]:  # Limit to 10 hero products
            href = link.css('::attr(href)').get()
            if href:
                product_url = urljoin(response.url, href)
                
                # Get product name
                name = (
                    link.css('::attr(title)').get() or
                    link.css('::attr(aria-label)').get() or
                    link.css('::text').get()
                )
                
                if name:
                    name = name.strip()
                    
                    # Get price if available
                    price = link.css('.price::text, .money::text, [class*="price"]::text').get()
                    if price:
                        price = price.strip()
                    
                    # Get image if available
                    img = link.css('img::attr(src)').get()
                    if img:
                        img = urljoin(response.url, img)
                    
                    hero_products.append({
                        'name': name,
                        'url': product_url,
                        'price': price,
                        'image': img
                    })
        
        return hero_products
    
    def _extract_social_handles(self, response):
        """Extract social media handles."""
        social_handles = []
        
        # Common social media patterns
        social_patterns = {
            'instagram': r'instagram\.com/([^/\s\?]+)',
            'facebook': r'facebook\.com/([^/\s\?]+)',
            'twitter': r'twitter\.com/([^/\s\?]+)',
            'youtube': r'youtube\.com/(channel/|user/|c/|@)?([^/\s\?]+)',
            'tiktok': r'tiktok\.com/@?([^/\s\?]+)',
            'linkedin': r'linkedin\.com/(company/|in/)?([^/\s\?]+)',
            'pinterest': r'pinterest\.com/([^/\s\?]+)'
        }
        
        html_text = response.text
        
        for platform, pattern in social_patterns.items():
            matches = re.finditer(pattern, html_text, re.IGNORECASE)
            for match in matches:
                handle = match.group(1) if len(match.groups()) == 1 else match.group(2)
                if handle and handle not in ['share', 'intent', 'sharer']:
                    social_handles.append({
                        'platform': platform,
                        'handle': handle,
                        'url': match.group(0)
                    })
                    break  # Only one per platform
        
        return social_handles
    
    def _extract_important_links(self, response):
        """Extract important links."""
        important_links = []
        
        # Look for specific types of links
        link_patterns = {
            'tracking': ['track', 'tracking', 'order-status'],
            'contact': ['contact', 'contact-us'],
            'blog': ['blog', 'news', 'articles'],
            'support': ['support', 'help', 'customer-service'],
            'about': ['about', 'our-story'],
            'legal': ['legal', 'terms', 'privacy']
        }
        
        # Get all links from footer and header
        footer_links = response.css('footer a')
        header_links = response.css('header a, nav a')
        all_links = footer_links + header_links
        
        for link in all_links[:20]:  # Limit to avoid too many links
            href = link.css('::attr(href)').get()
            text = link.css('::text').get()
            
            if href and text:
                text = text.strip()
                href = urljoin(response.url, href)
                
                # Categorize the link
                category = 'other'
                for cat, keywords in link_patterns.items():
                    if any(kw in href.lower() or kw in text.lower() for kw in keywords):
                        category = cat
                        break
                
                if category != 'other':
                    important_links.append({
                        'name': text[:50],
                        'url': href,
                        'category': category
                    })
        
        return important_links
    
    def _extract_faqs_from_response(self, response):
        """Extract FAQs from page content."""
        faqs = []
        
        # Try schema markup first
        faq_scripts = response.css('script[type="application/ld+json"]::text').getall()
        for script_text in faq_scripts:
            try:
                data = json.loads(script_text)
                if data.get('@type') == 'FAQPage' and 'mainEntity' in data:
                    for item in data['mainEntity']:
                        if item.get('@type') == 'Question':
                            question = item.get('name', '')
                            answer = item.get('acceptedAnswer', {}).get('text', '')
                            if question and answer:
                                faqs.append({
                                    'question': question,
                                    'answer': answer[:500]  # Limit answer length
                                })
            except:
                continue
        
        # If no schema FAQs, try HTML patterns
        if not faqs:
            # Look for common FAQ structures
            faq_items = response.css('.faq-item, .accordion-item, details')
            for item in faq_items[:10]:  # Limit to 10 FAQs
                question = item.css('.faq-question::text, .accordion-title::text, summary::text').get()
                answer = item.css('.faq-answer::text, .accordion-content::text').get()
                
                if question and answer:
                    faqs.append({
                        'question': question.strip(),
                        'answer': answer.strip()[:500]
                    })
        
        return faqs
    
    def _extract_contact_info(self, response):
        """Extract contact information."""
        text = response.text
        
        # Extract emails
        emails = EmailPhoneExtractor.extract_emails(text)[:3]
        
        # Extract phone numbers
        phones = EmailPhoneExtractor.extract_phone_numbers(text)[:3]
        
        # Extract address
        address = None
        address_elem = response.css('address::text, .address::text, [class*="address"]::text').get()
        if address_elem:
            address = address_elem.strip()[:200]
        
        return {
            'emails': emails,
            'phones': phones,
            'address': address
        }
    
    def _extract_main_content(self, response):
        """Extract main content from page."""
        # Try different content selectors
        for selector in CONTENT_SELECTORS:
            content = response.css(f'{selector}::text').getall()
            if content:
                return ' '.join(content).strip()
        
        # Fallback to body text
        body_text = ' '.join(response.css('body::text').getall())
        return body_text.strip()
    
    def _get_policy_type(self, path):
        """Determine policy type from URL path."""
        path_lower = path.lower()
        if 'privacy' in path_lower:
            return 'privacy_policy'
        elif 'return' in path_lower or 'refund' in path_lower:
            return 'return_refund_policy'
        elif 'shipping' in path_lower:
            return 'shipping_policy'
        elif 'terms' in path_lower:
            return 'terms_of_service'
        return 'unknown'
    
    def _get_page_type(self, path):
        """Determine page type from URL path."""
        path_lower = path.lower()
        if 'faq' in path_lower:
            return 'faq'
        elif 'about' in path_lower or 'story' in path_lower:
            return 'about'
        elif 'contact' in path_lower:
            return 'contact'
        return 'unknown'


class ScrapyShopifyScraperService:
    """Service for scraping Shopify stores using Scrapy."""
    
    def __init__(self):
        self.scraping_settings = get_scraping_settings()
        self.shopify_settings = get_shopify_settings()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    async def extract_insights(self, website_url: str) -> BrandInsights:
        """Extract all insights from a Shopify store using Scrapy."""
        start_time = datetime.utcnow()
        normalized_url = URLValidator.normalize_url(website_url)
        
        insights = BrandInsights(website_url=normalized_url)
        
        try:
            print(f"Starting Scrapy extraction from: {normalized_url}")
            
            # Run Scrapy spider
            scraped_data = await self._run_spider(normalized_url)
            
            if scraped_data.get('error'):
                if 'not found' in scraped_data['error'].lower():
                    raise WebsiteNotFoundException(normalized_url)
                elif 'not a shopify store' in scraped_data['error'].lower():
                    raise NotShopifyStoreException(normalized_url)
                else:
                    raise ScrapingException(normalized_url, scraped_data['error'])
            
            # Process scraped data
            insights = self._process_scraped_data(scraped_data, insights)
            
            # Calculate extraction duration
            end_time = datetime.utcnow()
            insights.extraction_duration_seconds = (end_time - start_time).total_seconds()
            print(f"Scrapy extraction completed in {insights.extraction_duration_seconds:.2f} seconds")
            
        except Exception as e:
            insights.extraction_success = False
            insights.error_messages.append(str(e))
            print(f"Scrapy extraction failed: {e}")
            raise
        
        return insights
    
    async def _run_spider(self, url: str) -> Dict[str, Any]:
        """Run the Scrapy spider and return extracted data."""
        # Configure Scrapy settings
        settings = get_project_settings()
        settings.setdict({
            'LOG_LEVEL': 'ERROR',  # Reduce logging noise
            'ROBOTSTXT_OBEY': False,
            'DOWNLOAD_DELAY': 0.5,
            'RANDOMIZE_DOWNLOAD_DELAY': True,
            'CONCURRENT_REQUESTS': 2,
            'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
            'COOKIES_ENABLED': True,
            'RETRY_ENABLED': True,
            'RETRY_TIMES': 2,
            'DOWNLOAD_TIMEOUT': 30,
            'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Store results
        insights_data = {}
        
        # Create and run spider
        def run_spider():
            from twisted.internet import reactor
            
            runner = CrawlerRunner(settings)
            deferred = runner.crawl(ShopifySpider, start_url=url, insights_data=insights_data)
            deferred.addBoth(lambda _: reactor.stop())
            reactor.run(installSignalHandlers=False)
            
            return insights_data
        
        # Run in thread to avoid blocking
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, run_spider)
        
        return result
    
    def _process_scraped_data(self, scraped_data: Dict, insights: BrandInsights) -> BrandInsights:
        """Process the scraped data into BrandInsights object."""
        
        # Basic info
        insights.brand_name = scraped_data.get('brand_name')
        insights.is_shopify_store = scraped_data.get('is_shopify', False)
        
        # Products
        products_json = scraped_data.get('products_json', [])
        insights.product_catalog = self._process_products(products_json)
        insights.total_products = len(insights.product_catalog)
        
        # Hero products
        hero_data = scraped_data.get('hero_products', [])
        insights.hero_products = self._process_hero_products(hero_data)
        
        # Policies
        policies = scraped_data.get('policies', {})
        for policy_type, policy_data in policies.items():
            if policy_type == 'privacy_policy':
                insights.privacy_policy = policy_data.get('content')
                insights.privacy_policy_url = policy_data.get('url')
            elif policy_type == 'return_refund_policy':
                insights.return_refund_policy = policy_data.get('content')
                insights.return_refund_policy_url = policy_data.get('url')
            elif policy_type == 'shipping_policy':
                insights.shipping_policy = policy_data.get('content')
            elif policy_type == 'terms_of_service':
                insights.terms_of_service = policy_data.get('content')
        
        # FAQs
        faqs_data = scraped_data.get('faqs', [])
        insights.faqs = [FAQ(question=faq['question'], answer=faq['answer']) for faq in faqs_data]
        
        # Social handles
        social_data = scraped_data.get('social_handles', [])
        insights.social_handles = [
            SocialHandle(
                platform=social['platform'],
                url=social['url'],
                handle=social['handle']
            ) for social in social_data
        ]
        
        # Contact info
        contact_data = scraped_data.get('contact_info', {})
        insights.contact_info = ContactInfo(
            emails=contact_data.get('emails', []),
            phone_numbers=contact_data.get('phones', []),
            address=contact_data.get('address')
        )
        
        # Brand context
        insights.brand_context = scraped_data.get('brand_context')
        
        # Important links
        links_data = scraped_data.get('important_links', [])
        insights.important_links = [
            ImportantLink(
                name=link['name'],
                url=link['url'],
                category=link['category']
            ) for link in links_data
        ]
        
        return insights
    
    def _process_products(self, products_json: List[Dict]) -> List[ProductInfo]:
        """Convert products JSON to ProductInfo objects."""
        products = []
        
        for product_data in products_json:
            try:
                product = ProductInfo(
                    name=product_data.get('title', ''),
                    description=product_data.get('body_html', ''),
                    vendor=product_data.get('vendor'),
                    product_type=product_data.get('product_type'),
                    tags=product_data.get('tags', '').split(', ') if product_data.get('tags') else [],
                    product_url=product_data.get('handle', '')
                )
                
                # Get first variant for price
                if product_data.get('variants'):
                    first_variant = product_data['variants'][0]
                    product.price = first_variant.get('price')
                    product.sku = first_variant.get('sku')
                    product.available = first_variant.get('available', True)
                
                # Get first image
                if product_data.get('images'):
                    product.image_url = product_data['images'][0].get('src')
                
                products.append(product)
            except Exception as e:
                continue
        
        return products
    
    def _process_hero_products(self, hero_data: List[Dict]) -> List[ProductInfo]:
        """Convert hero products data to ProductInfo objects."""
        hero_products = []
        
        for hero in hero_data:
            try:
                product = ProductInfo(
                    name=hero.get('name', ''),
                    product_url=hero.get('url'),
                    price=hero.get('price'),
                    image_url=hero.get('image')
                )
                hero_products.append(product)
            except Exception:
                continue
        
        return hero_products
