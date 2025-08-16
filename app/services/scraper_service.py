"""Shopify store scraper service using crawl4ai."""

import asyncio
import json
import re
from typing import List, Dict, Optional, Any
from datetime import datetime
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

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


class ShopifyScraperService:
    """Service for scraping Shopify stores using crawl4ai."""
    
    def __init__(self):
        self.session = None
        self.scraping_settings = get_scraping_settings()
        self.shopify_settings = get_shopify_settings()
        
        # Configure crawl4ai
        self.browser_config = BrowserConfig(
            headless=self.scraping_settings.headless_browser,
            verbose=False,
            browser_type="chromium"
        )
        self.crawler_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            screenshot=False,
            pdf=False,
            remove_overlay_elements=True,
            process_iframes=False,
            page_timeout=15000  # Reduced timeout
        )
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': self.scraping_settings.user_agent},
            timeout=aiohttp.ClientTimeout(total=self.scraping_settings.request_timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def extract_insights(self, website_url: str) -> BrandInsights:
        """
        Extract all 9 mandatory insights from a Shopify store.
        
        1. Whole Product Catalog
        2. Hero Products
        3. Privacy Policy
        4. Return/Refund Policies
        5. Brand FAQs
        6. Social Handles
        7. Contact Details
        8. Brand Context (About)
        9. Important Links
        """
        start_time = datetime.utcnow()
        normalized_url = URLValidator.normalize_url(website_url)
        
        insights = BrandInsights(website_url=normalized_url)
        
        try:
            # Fetch homepage with crawl4ai
            print(f"Fetching homepage: {normalized_url}")
            html_content = await self._fetch_page_with_crawl4ai(normalized_url)
            
            # Check if it's a Shopify store
            is_shopify = await ShopifyDetector.is_shopify_store(normalized_url, html_content)
            if not is_shopify:
                raise NotShopifyStoreException(normalized_url)
            
            insights.is_shopify_store = True
            
            # Extract Shopify metadata
            shopify_data = ShopifyDetector.extract_shopify_data_from_html(html_content)
            insights.currency = shopify_data.get('currency')
            insights.country = shopify_data.get('country')
            insights.brand_name = shopify_data.get('shop_name')
            
            print(f"Detected Shopify store: {insights.brand_name or 'Unknown'}")
            
            # Run all extraction tasks
            tasks = [
                self._extract_with_retry("Product Catalog", self.get_product_catalog(normalized_url)),
                self._extract_with_retry("Hero Products", self.get_hero_products(normalized_url, html_content)),
                self._extract_with_retry("Policies", self.extract_policies(normalized_url)),
                self._extract_with_retry("FAQs", self.extract_faqs(normalized_url)),
                self._extract_with_retry("Social Handles", self.extract_social_handles(normalized_url, html_content)),
                self._extract_with_retry("Contact Info", self.extract_contact_info(normalized_url, html_content)),
                self._extract_with_retry("Brand Context", self.extract_brand_context(normalized_url)),
                self._extract_with_retry("Important Links", self.extract_important_links(normalized_url, html_content))
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, (name, result) in enumerate(zip(
                ["Product Catalog", "Hero Products", "Policies", "FAQs", 
                 "Social Handles", "Contact Info", "Brand Context", "Important Links"],
                results
            )):
                if isinstance(result, Exception):
                    print(f"{name} extraction failed: {str(result)}")
                    insights.error_messages.append(f"{name}: {str(result)}")
                    continue
                
                if name == "Product Catalog":
                    insights.product_catalog = result
                    insights.total_products = len(result)
                    print(f"Found {len(result)} products")
                elif name == "Hero Products":
                    insights.hero_products = result
                    print(f"Found {len(result)} hero products")
                elif name == "Policies":
                    insights.privacy_policy = result.get('privacy_policy')
                    insights.privacy_policy_url = result.get('privacy_policy_url')
                    insights.return_refund_policy = result.get('return_refund_policy')
                    insights.return_refund_policy_url = result.get('return_refund_policy_url')
                    insights.shipping_policy = result.get('shipping_policy')
                    insights.terms_of_service = result.get('terms_of_service')
                    print(f"Extracted policies")
                elif name == "FAQs":
                    insights.faqs = result
                    print(f"Found {len(result)} FAQs")
                elif name == "Social Handles":
                    insights.social_handles = result
                    print(f"Found {len(result)} social handles")
                elif name == "Contact Info":
                    insights.contact_info = result
                    print(f"Extracted contact info")
                elif name == "Brand Context":
                    insights.brand_context = result
                    print(f"Extracted brand context")
                elif name == "Important Links":
                    insights.important_links = result
                    print(f"Found {len(result)} important links")
            
            # Calculate extraction duration
            end_time = datetime.utcnow()
            insights.extraction_duration_seconds = (end_time - start_time).total_seconds()
            print(f"Extraction completed in {insights.extraction_duration_seconds:.2f} seconds")
            
        except Exception as e:
            insights.extraction_success = False
            insights.error_messages.append(str(e))
            raise
        
        return insights
    
    async def _extract_with_retry(self, name: str, coro):
        """Helper to extract with error handling."""
        try:
            return await coro
        except Exception as e:
            print(f"Error extracting {name}: {e}")
            raise
    
    async def _fetch_page_with_crawl4ai(self, url: str) -> str:
        """Fetch page content using crawl4ai."""
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            result = await crawler.arun(
                url=url,
                config=self.crawler_config
            )
            
            if result.success:
                return result.cleaned_html or result.html
            else:
                raise ScrapingException(url, result.error_message or "Failed to fetch page")
    
    async def _fetch_json(self, url: str) -> Optional[Dict]:
        """Fetch JSON data from URL."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            print(f"Error fetching JSON from {url}: {e}")
        return None
    
    async def get_product_catalog(self, base_url: str) -> List[ProductInfo]:
        """Extract product catalog from /products.json endpoint."""
        products_url = urljoin(base_url, self.shopify_settings.products_endpoint)
        print(f"Fetching products from: {products_url}")
        products_data = await self._fetch_json(products_url)
        
        if not products_data or 'products' not in products_data:
            return []
        
        products = []
        max_products = self.scraping_settings.max_products_to_fetch
        
        for product_data in products_data['products'][:max_products]:
            try:
                product = ProductInfo(
                    name=product_data.get('title', ''),
                    description=product_data.get('body_html', ''),
                    vendor=product_data.get('vendor'),
                    product_type=product_data.get('product_type'),
                    tags=product_data.get('tags', '').split(', ') if product_data.get('tags') else [],
                    product_url=urljoin(base_url, f"/products/{product_data.get('handle')}") if product_data.get('handle') else None
                )
                
                # Get first variant for price and availability
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
    
    async def get_hero_products(self, base_url: str, html_content: Optional[str] = None) -> List[ProductInfo]:
        """Extract hero/featured products from homepage."""
        if not html_content:
            html_content = await self._fetch_page_with_crawl4ai(base_url)
        
        soup = BeautifulSoup(html_content, 'lxml')
        hero_products = []
        max_hero = self.scraping_settings.max_hero_products
        
        for selector in HERO_PRODUCT_SELECTORS:
            sections = soup.select(selector)
            for section in sections:
                product_links = section.select('a[href*="/products/"]')
                for link in product_links[:max_hero]:
                    product_url = urljoin(base_url, link.get('href', ''))
                    product_name = link.get('title') or link.text.strip()
                    
                    if product_name:
                        product = ProductInfo(
                            name=product_name,
                            product_url=product_url
                        )
                        
                        # Try to find price
                        price_elem = link.find_next(class_=re.compile(r'price|money'))
                        if price_elem:
                            product.price = price_elem.text.strip()
                        
                        # Try to find image
                        img_elem = link.find('img')
                        if img_elem and img_elem.get('src'):
                            product.image_url = urljoin(base_url, img_elem['src'])
                        
                        hero_products.append(product)
                        
                        if len(hero_products) >= max_hero:
                            return hero_products
        
        return hero_products[:max_hero]
    
    async def extract_policies(self, base_url: str) -> Dict[str, Optional[str]]:
        """Extract privacy, return/refund, shipping policies."""
        policies = {}
        
        # Define policy URLs from settings
        policy_configs = [
            ('privacy_policy', self.shopify_settings.policy_paths),
            ('return_refund_policy', self.shopify_settings.return_policy_paths),
            ('shipping_policy', self.shopify_settings.shipping_policy_paths),
            ('terms_of_service', self.shopify_settings.terms_paths)
        ]
        
        tasks = []
        for policy_type, urls in policy_configs:
            tasks.append(self._fetch_policy(base_url, policy_type, urls))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, dict):
                policies.update(result)
        
        return policies
    
    async def _fetch_policy(self, base_url: str, policy_type: str, urls: List[str]) -> Dict:
        """Fetch a specific policy from possible URLs."""
        for url_path in urls:
            try:
                full_url = urljoin(base_url, url_path)
                html = await self._fetch_page_with_crawl4ai(full_url)
                soup = BeautifulSoup(html, 'lxml')
                
                # Find main content
                content = None
                for selector in CONTENT_SELECTORS:
                    elem = soup.select_one(selector)
                    if elem:
                        content = elem.get_text(separator='\n', strip=True)
                        break
                
                if content and len(content) > MIN_POLICY_LENGTH:
                    max_length = self.scraping_settings.max_policy_length
                    return {
                        policy_type: content[:max_length],
                        f"{policy_type}_url": full_url
                    }
            except Exception:
                continue
        
        return {policy_type: None, f"{policy_type}_url": None}
    
    async def extract_faqs(self, base_url: str) -> List[FAQ]:
        """Extract FAQs from various formats."""
        for url_path in self.shopify_settings.faq_paths:
            try:
                full_url = urljoin(base_url, url_path)
                html = await self._fetch_page_with_crawl4ai(full_url)
                faqs = self._parse_faqs_from_html(html)
                if faqs:
                    return faqs
            except Exception:
                continue
        
        return []
    
    def _parse_faqs_from_html(self, html: str) -> List[FAQ]:
        """Parse FAQs from HTML using multiple patterns."""
        soup = BeautifulSoup(html, 'lxml')
        faqs = []
        max_faqs = self.scraping_settings.max_faqs
        
        # Pattern 1: FAQ schema markup
        schema_scripts = soup.find_all('script', type='application/ld+json')
        for script in schema_scripts:
            try:
                data = json.loads(script.string)
                if data.get('@type') == 'FAQPage' and 'mainEntity' in data:
                    for item in data['mainEntity']:
                        if item.get('@type') == 'Question':
                            faq = FAQ(
                                question=item.get('name', ''),
                                answer=item.get('acceptedAnswer', {}).get('text', '')
                            )
                            faqs.append(faq)
            except:
                continue
        
        if faqs:
            return faqs[:max_faqs]
        
        # Pattern 2: HTML patterns
        for pattern in FAQ_PATTERNS:
            containers = soup.select(pattern['container'])
            for container in containers[:max_faqs]:
                question_elem = container.select_one(pattern['question'])
                if question_elem:
                    question = question_elem.get_text(strip=True)
                    
                    if pattern['answer']:
                        answer_elem = container.select_one(pattern['answer'])
                        answer = answer_elem.get_text(strip=True) if answer_elem else ''
                    else:
                        # For details/summary pattern
                        answer = container.get_text(strip=True).replace(question, '', 1).strip()
                    
                    if question and answer:
                        max_answer_length = self.scraping_settings.max_faq_answer_length
                        faqs.append(FAQ(question=question, answer=answer[:max_answer_length]))
        
        return faqs[:max_faqs]
    
    async def extract_social_handles(self, base_url: str, html_content: Optional[str] = None) -> List[SocialHandle]:
        """Extract social media handles from the website."""
        if not html_content:
            html_content = await self._fetch_page_with_crawl4ai(base_url)
        
        social_links = SocialMediaExtractor.extract_social_links(html_content)
        social_handles = []
        max_social = self.scraping_settings.max_social_handles
        
        for platform, url in social_links[:max_social]:
            handle = SocialMediaExtractor.extract_handle_from_url(url)
            social_handles.append(
                SocialHandle(
                    platform=platform,
                    url=url,
                    handle=handle
                )
            )
        
        return social_handles
    
    async def extract_contact_info(self, base_url: str, html_content: Optional[str] = None) -> ContactInfo:
        """Extract contact information (emails, phones, address)."""
        contact_info = ContactInfo()
        
        # Try to fetch contact page
        contact_html = None
        for url_path in self.shopify_settings.contact_paths:
            try:
                full_url = urljoin(base_url, url_path)
                contact_html = await self._fetch_page_with_crawl4ai(full_url)
                break
            except:
                continue
        
        # Combine homepage and contact page content
        all_content = (html_content or '') + (contact_html or '')
        
        # Extract emails and phones
        contact_info.emails = EmailPhoneExtractor.extract_emails(all_content)[:3]
        contact_info.phone_numbers = EmailPhoneExtractor.extract_phone_numbers(all_content)[:3]
        
        # Try to extract address
        soup = BeautifulSoup(all_content, 'lxml')
        address_patterns = [
            'div[class*="address"]',
            'address',
            'div[class*="location"]',
            'p[class*="address"]'
        ]
        
        for pattern in address_patterns:
            elem = soup.select_one(pattern)
            if elem:
                contact_info.address = elem.get_text(strip=True)[:200]
                break
        
        return contact_info
    
    async def extract_brand_context(self, base_url: str) -> Optional[str]:
        """Extract brand context/about information."""
        for url_path in self.shopify_settings.about_paths:
            try:
                full_url = urljoin(base_url, url_path)
                html = await self._fetch_page_with_crawl4ai(full_url)
                soup = BeautifulSoup(html, 'lxml')
                
                # Find main content
                for selector in CONTENT_SELECTORS:
                    elem = soup.select_one(selector)
                    if elem:
                        text = elem.get_text(separator=' ', strip=True)
                        if len(text) > MIN_BRAND_CONTEXT_LENGTH:
                            max_length = self.scraping_settings.max_brand_context_length
                            return text[:max_length]
            except:
                continue
        
        return None
    
    async def extract_important_links(self, base_url: str, html_content: Optional[str] = None) -> List[ImportantLink]:
        """Extract important links like order tracking, contact, blogs."""
        if not html_content:
            html_content = await self._fetch_page_with_crawl4ai(base_url)
        
        soup = BeautifulSoup(html_content, 'lxml')
        important_links = []
        max_links = self.scraping_settings.max_important_links
        
        # Define link patterns
        link_patterns = {
            'tracking': ['track', 'tracking', 'order-status'],
            'contact': ['contact', 'contact-us'],
            'blog': ['blog', 'news', 'articles'],
            'support': ['support', 'help', 'customer-service'],
            'about': ['about', 'our-story'],
            'legal': ['legal', 'terms', 'privacy']
        }
        
        # Find all links in footer and header
        footer = soup.find('footer') or soup
        header = soup.find('header') or soup
        
        all_links = footer.find_all('a', href=True) + header.find_all('a', href=True)
        
        seen_urls = set()
        for link in all_links:
            href = link['href']
            text = link.get_text(strip=True)
            
            if not text or href in seen_urls:
                continue
            
            full_url = urljoin(base_url, href)
            seen_urls.add(href)
            
            # Categorize the link
            category = 'other'
            for cat, keywords in link_patterns.items():
                if any(kw in href.lower() or kw in text.lower() for kw in keywords):
                    category = cat
                    break
            
            if category != 'other':
                important_links.append(
                    ImportantLink(
                        name=text[:50],
                        url=full_url,
                        category=category
                    )
                )
                
                if len(important_links) >= max_links:
                    break
        
        return important_links