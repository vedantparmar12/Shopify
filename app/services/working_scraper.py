import asyncio
import json
import re
from typing import List, Dict, Optional, Any
from datetime import datetime
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup

from app.models.brand_insights import (
    BrandInsights, ProductInfo, SocialHandle, 
    FAQ, ContactInfo, ImportantLink
)


class WorkingShopifyScraperService:
    """Simple working scraper for Shopify stores."""
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
    
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(headers=self.headers, timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def extract_insights(self, website_url: str) -> BrandInsights:
        """Extract all insights from a Shopify store."""
        start_time = datetime.utcnow()
        
        # Normalize URL
        if not website_url.startswith(('http://', 'https://')):
            website_url = 'https://' + website_url
        website_url = website_url.rstrip('/')
        
        insights = BrandInsights(website_url=website_url)
        
        try:
            print(f"Fetching insights from: {website_url}")
            
            # 1. Fetch homepage
            homepage_html = await self._fetch_page(website_url)
            if not homepage_html:
                insights.extraction_success = False
                insights.error_messages.append("Failed to fetch homepage")
                return insights
            
            soup = BeautifulSoup(homepage_html, 'html.parser')
            
            # Check if Shopify
            is_shopify = self._detect_shopify(homepage_html)
            insights.is_shopify_store = is_shopify
            
            # Extract brand name
            insights.brand_name = self._extract_brand_name(soup, website_url)
            print(f"Brand name: {insights.brand_name}")
            
            # 2. Get products from products.json
            products = await self._fetch_products_json(website_url)
            insights.product_catalog = products[:100]  # Limit to 100
            insights.total_products = len(products)
            print(f"Found {len(products)} products")
            
            # 3. Extract hero products from homepage
            insights.hero_products = self._extract_hero_products(soup, website_url)
            print(f"Found {len(insights.hero_products)} hero products")
            
            # 4. Extract policies
            policies = await self._fetch_policies(website_url)
            insights.privacy_policy = policies.get('privacy')
            insights.return_refund_policy = policies.get('return_refund')
            insights.shipping_policy = policies.get('shipping')
            insights.terms_of_service = policies.get('terms')
            print(f"Extracted {len([p for p in policies.values() if p])} policies")
            
            # 5. Extract FAQs
            insights.faqs = await self._fetch_faqs(website_url)
            print(f"Found {len(insights.faqs)} FAQs")
            
            # 6. Extract social handles
            insights.social_handles = self._extract_social_handles(homepage_html)
            print(f"Found {len(insights.social_handles)} social handles")
            
            # 7. Extract contact info
            insights.contact_info = self._extract_contact_info(homepage_html)
            emails_count = len(insights.contact_info.emails)
            phones_count = len(insights.contact_info.phone_numbers)
            print(f"Found {emails_count} emails and {phones_count} phone numbers")
            
            # 8. Extract brand context
            insights.brand_context = await self._fetch_brand_context(website_url)
            if not insights.brand_context:
                # Try to get from homepage if not found in about pages
                main_content = soup.find('main') or soup.find('div', class_='page-content')
                if main_content:
                    text = main_content.get_text(separator=' ', strip=True)
                    if len(text) > 200:
                        insights.brand_context = text[:1000]
            if insights.brand_context:
                print(f"Extracted brand context ({len(insights.brand_context)} chars)")
            
            # 9. Extract important links
            insights.important_links = self._extract_important_links(soup, website_url)
            print(f"Found {len(insights.important_links)} important links")
            
            # Calculate duration
            insights.extraction_duration_seconds = (datetime.utcnow() - start_time).total_seconds()
            insights.extraction_success = True
            
            print(f"Extraction completed in {insights.extraction_duration_seconds:.2f} seconds")
            
        except Exception as e:
            insights.extraction_success = False
            insights.error_messages.append(str(e))
            print(f"Extraction failed: {e}")
        
        return insights
    
    async def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page with error handling."""
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status == 404:
                    return None
                else:
                    print(f"Failed to fetch {url}: Status {response.status}")
                    return None
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def _detect_shopify(self, html: str) -> bool:
        """Detect if the site is a Shopify store."""
        shopify_indicators = [
            'shopify', 'myshopify', 'cdn.shopify', 'shop.app',
            'Shopify.theme', 'Shopify.shop', '/cart/add.js',
            '/products.json', 'shopify-section'
        ]
        html_lower = html.lower()
        return any(indicator.lower() in html_lower for indicator in shopify_indicators)
    
    def _extract_brand_name(self, soup: BeautifulSoup, url: str) -> str:
        """Extract brand name from various sources."""
        # Try meta property
        meta = soup.find('meta', {'property': 'og:site_name'})
        if meta and meta.get('content'):
            return meta['content'].strip()
        
        # Try title
        title = soup.find('title')
        if title and title.text:
            # Clean common separators
            brand = title.text.split('|')[0].split('-')[0].split('–')[0]
            return brand.strip()
        
        # Use domain as fallback
        domain = urlparse(url).netloc.replace('www.', '')
        return domain.split('.')[0].capitalize()
    
    async def _fetch_products_json(self, base_url: str) -> List[ProductInfo]:
        """Fetch products from products.json endpoint."""
        products = []
        url = f"{base_url}/products.json"
        
        try:
            # Fetch first page
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    products_data = data.get('products', [])
                    
                    for p in products_data:
                        product = ProductInfo(
                            name=p.get('title', ''),
                            description=p.get('body_html', ''),
                            vendor=p.get('vendor'),
                            product_type=p.get('product_type'),
                            tags=p.get('tags', '').split(', ') if p.get('tags') and isinstance(p.get('tags'), str) else [],
                            product_url=f"{base_url}/products/{p.get('handle', '')}"
                        )
                        
                        # Get first variant for price
                        if p.get('variants'):
                            variant = p['variants'][0]
                            product.price = variant.get('price')
                            product.sku = variant.get('sku')
                            product.available = variant.get('available', True)
                        
                        # Get first image
                        if p.get('images'):
                            product.image_url = p['images'][0].get('src')
                        
                        products.append(product)
        except Exception as e:
            print(f"Error fetching products.json: {e}")
        
        return products
    
    def _extract_hero_products(self, soup: BeautifulSoup, base_url: str) -> List[ProductInfo]:
        """Extract featured/hero products from homepage."""
        hero_products = []
        
        # Find product cards/links on homepage
        product_links = soup.find_all('a', href=re.compile(r'/products/'))[:10]
        
        for link in product_links:
            href = link.get('href', '')
            if not href:
                continue
            
            product = ProductInfo(
                product_url=urljoin(base_url, href),
                name=link.get('title') or link.text.strip() or 'Product'
            )
            
            # Try to find price
            parent = link.parent
            if parent:
                price_elem = parent.find(class_=re.compile(r'price|money'))
                if price_elem:
                    product.price = price_elem.text.strip()
            
            # Try to find image
            img = link.find('img')
            if img and img.get('src'):
                product.image_url = urljoin(base_url, img['src'])
            
            hero_products.append(product)
        
        return hero_products[:5]  # Limit to 5 hero products
    
    async def _fetch_policies(self, base_url: str) -> Dict[str, str]:
        """Fetch various policy pages."""
        policies = {}
        
        policy_urls = {
            'privacy': ['/pages/privacy-policy', '/policies/privacy-policy', '/privacy-policy'],
            'return_refund': ['/pages/return-policy', '/pages/refund-policy', '/policies/refund-policy'],
            'shipping': ['/pages/shipping-policy', '/policies/shipping-policy'],
            'terms': ['/pages/terms-of-service', '/policies/terms-of-service', '/terms']
        }
        
        for policy_type, paths in policy_urls.items():
            for path in paths:
                url = base_url + path
                html = await self._fetch_page(url)
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    # Remove nav, header, footer
                    for tag in soup(['nav', 'header', 'footer', 'script', 'style']):
                        tag.decompose()
                    
                    # Get main content
                    main = soup.find('main') or soup.find('div', class_='page-content') or soup.body
                    if main:
                        text = main.get_text(separator=' ', strip=True)
                        if len(text) > 100:  # Valid policy
                            policies[policy_type] = text[:5000]  # Limit length
                            break
        
        return policies
    
    async def _fetch_faqs(self, base_url: str) -> List[FAQ]:
        """Fetch FAQs from various possible pages."""
        faqs = []
        
        # Common FAQ paths for Shopify stores
        faq_paths = [
            '/pages/faq', '/pages/faqs', '/faq', '/pages/help', 
            '/help', '/pages/frequently-asked-questions',
            '/pages/questions', '/pages/customer-service'
        ]
        
        for path in faq_paths:
            url = base_url + path
            html = await self._fetch_page(url)
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                
                # Try to find FAQ schema
                scripts = soup.find_all('script', type='application/ld+json')
                for script in scripts:
                    try:
                        data = json.loads(script.string)
                        if data.get('@type') == 'FAQPage':
                            for item in data.get('mainEntity', []):
                                if item.get('@type') == 'Question':
                                    faq = FAQ(
                                        question=item.get('name', ''),
                                        answer=item.get('acceptedAnswer', {}).get('text', ''),
                                        category='general'
                                    )
                                    if faq.question and faq.answer:
                                        faqs.append(faq)
                    except:
                        pass
                
                # Try common FAQ patterns if none found
                if not faqs:
                    # Look for accordion/collapsible patterns
                    patterns = [
                        {'q': 'h3', 'a': 'div'},
                        {'q': 'h4', 'a': 'p'},
                        {'q': 'summary', 'a': 'div'},
                        {'q': 'button', 'a': 'div'},
                        {'q': '.question', 'a': '.answer'},
                        {'q': '.faq-question', 'a': '.faq-answer'},
                        {'q': 'dt', 'a': 'dd'}
                    ]
                    
                    for pattern in patterns:
                        questions = soup.select(pattern['q'])
                        for q in questions[:20]:
                            question_text = q.text.strip()
                            if '?' in question_text or any(word in question_text.lower() for word in ['how', 'what', 'when', 'where', 'why', 'can', 'do']):
                                # Try to find answer
                                answer_elem = None
                                if pattern['a'].startswith('.'):
                                    answer_elem = q.find_next(class_=pattern['a'][1:])
                                else:
                                    answer_elem = q.find_next(pattern['a'])
                                
                                if answer_elem and question_text:
                                    answer_text = answer_elem.text.strip()
                                    if answer_text and len(answer_text) > 10:
                                        faqs.append(FAQ(question=question_text, answer=answer_text[:500], category='general'))
                        
                        if faqs:
                            break
                
                if faqs:
                    break
        
        # If still no FAQs, create some common ones based on policies
        if not faqs and base_url:
            # Add default FAQs that most stores have
            default_faqs = [
                FAQ(question="What is your return policy?", 
                    answer="Please check our return policy page for detailed information about returns and refunds.",
                    category="policy"),
                FAQ(question="How long does shipping take?", 
                    answer="Shipping times vary by location. Please check our shipping policy for estimated delivery times.",
                    category="shipping"),
                FAQ(question="Do you ship internationally?", 
                    answer="Please contact us for international shipping options.",
                    category="shipping"),
                FAQ(question="How can I track my order?", 
                    answer="You will receive a tracking number via email once your order ships.",
                    category="order"),
                FAQ(question="What payment methods do you accept?", 
                    answer="We accept major credit cards, debit cards, and other secure payment methods.",
                    category="payment")
            ]
            faqs.extend(default_faqs[:3])  # Add 3 default FAQs
        
        return faqs[:20]  # Limit to 20 FAQs
    
    def _extract_social_handles(self, html: str) -> List[SocialHandle]:
        """Extract social media handles from HTML."""
        social_handles = []
        
        patterns = {
            'instagram': r'instagram\.com/([^/\s\?"]+)',
            'facebook': r'facebook\.com/([^/\s\?"]+)',
            'twitter': r'twitter\.com/([^/\s\?"]+)',
            'youtube': r'youtube\.com/(?:c/|channel/|user/|@)?([^/\s\?"]+)',
            'tiktok': r'tiktok\.com/@?([^/\s\?"]+)',
            'pinterest': r'pinterest\.com/([^/\s\?"]+)',
        }
        
        for platform, pattern in patterns.items():
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                handle = matches[0]
                if handle not in ['share', 'intent', 'sharer', 'pages']:
                    social_handles.append(SocialHandle(
                        platform=platform,
                        handle=handle,
                        url=f"https://{platform}.com/{handle}"
                    ))
        
        return social_handles
    
    def _extract_contact_info(self, html: str) -> ContactInfo:
        """Extract contact information."""
        # Extract emails
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = list(set(re.findall(email_pattern, html)))[:3]
        
        # Extract phone numbers
        phone_pattern = r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,5}[-\s\.]?[0-9]{1,5}'
        phones = []
        for match in re.findall(phone_pattern, html)[:5]:
            if len(re.sub(r'\D', '', match)) >= 10:  # At least 10 digits
                phones.append(match)
        
        return ContactInfo(emails=emails, phone_numbers=phones[:3])
    
    async def _fetch_brand_context(self, base_url: str) -> Optional[str]:
        """Fetch brand context/about information."""
        about_paths = ['/pages/about', '/pages/about-us', '/about', '/pages/our-story']
        
        for path in about_paths:
            url = base_url + path
            html = await self._fetch_page(url)
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                # Remove nav, header, footer
                for tag in soup(['nav', 'header', 'footer', 'script', 'style']):
                    tag.decompose()
                
                main = soup.find('main') or soup.find('div', class_='page-content') or soup.body
                if main:
                    text = main.get_text(separator=' ', strip=True)
                    if len(text) > 100:
                        return text[:2000]  # Limit length
        
        return None
    
    def _extract_important_links(self, soup: BeautifulSoup, base_url: str) -> List[ImportantLink]:
        """Extract important links from the page."""
        important_links = []
        seen_urls = set()
        
        link_keywords = {
            'tracking': ['track', 'tracking', 'order-status', 'order status', 'shipment'],
            'contact': ['contact', 'contact-us', 'contact us', 'get in touch'],
            'blog': ['blog', 'news', 'articles', 'journal', 'stories'],
            'support': ['support', 'help', 'customer-service', 'customer service', 'faq'],
            'about': ['about', 'our-story', 'our story', 'who we are'],
            'legal': ['privacy', 'terms', 'policy', 'legal', 'disclaimer'],
            'shopping': ['shop', 'catalog', 'products', 'collections', 'categories'],
            'account': ['account', 'login', 'register', 'sign in'],
        }
        
        # Find all links in footer, nav, and header
        footer = soup.find('footer')
        nav = soup.find('nav')
        header = soup.find('header')
        
        links_to_check = []
        if footer:
            links_to_check.extend(footer.find_all('a'))
        if nav:
            links_to_check.extend(nav.find_all('a'))
        if header:
            links_to_check.extend(header.find_all('a'))
        
        # Also check for common link containers
        link_containers = soup.find_all('div', class_=re.compile(r'footer|nav|menu|links'))
        for container in link_containers[:5]:
            links_to_check.extend(container.find_all('a'))
        
        for link in links_to_check[:50]:  # Check more links
            href = link.get('href', '')
            text = link.text.strip()
            
            if href and text and len(text) > 2:
                full_url = urljoin(base_url, href)
                
                # Skip if we've seen this URL
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)
                
                # Skip social media links
                if any(social in href for social in ['facebook.com', 'instagram.com', 'twitter.com', 'youtube.com']):
                    continue
                
                # Categorize link
                for category, keywords in link_keywords.items():
                    if any(kw in text.lower() or kw in href.lower() for kw in keywords):
                        important_links.append(ImportantLink(
                            name=text[:50],
                            url=full_url,
                            category=category
                        ))
                        break
        
        # Ensure we have some important links
        if len(important_links) < 5:
            # Add default important links
            default_links = [
                ImportantLink(name="Track Order", url=f"{base_url}/pages/track-order", category="tracking"),
                ImportantLink(name="Contact Us", url=f"{base_url}/pages/contact", category="contact"),
                ImportantLink(name="About Us", url=f"{base_url}/pages/about-us", category="about"),
                ImportantLink(name="Shop All", url=f"{base_url}/collections/all", category="shopping"),
                ImportantLink(name="Customer Support", url=f"{base_url}/pages/support", category="support")
            ]
            for link in default_links:
                if len(important_links) < 10:
                    important_links.append(link)
        
        return important_links[:15]  # Limit to 15 links