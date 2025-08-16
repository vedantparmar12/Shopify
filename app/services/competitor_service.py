import asyncio
import aiohttp
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
import re

from app.models.brand_insights import BrandInsights
from app.utils.validators import URLValidator, ShopifyDetector


class CompetitorAnalysisService:
    def __init__(self):
        self.session = None
    
    async def find_competitors(
        self,
        brand_name: str,
        industry_keywords: Optional[List[str]] = None,
        max_results: int = 5
    ) -> List[str]:
        competitors = []
        seen_domains = set()
        
        # Build search queries based on industry keywords
        search_queries = []
        
        # Query 1: Industry-specific search
        if industry_keywords and len(industry_keywords) > 0:
            # Use the most relevant keywords for search
            primary_keywords = ' '.join(industry_keywords[:2])  # Use first 2 keywords
            search_queries.append(f"{primary_keywords} online store site:myshopify.com")
            search_queries.append(f"{primary_keywords} shop buy online")
            search_queries.append(f"best {primary_keywords} brands online")
        
        # Query 2: Brand-specific competitor search
        if brand_name:
            search_queries.append(f'"{brand_name}" competitors alternatives similar')
            search_queries.append(f'sites like {brand_name}')
        
        # Query 3: Generic industry search if keywords provided
        if industry_keywords:
            all_keywords = ' '.join(industry_keywords)
            search_queries.append(f"{all_keywords} shop")
        
        # Execute searches
        for query in search_queries[:3]:  # Limit to 3 searches to avoid rate limiting
            if query:
                found_urls = await self._search_google(query, max_results * 2)
                competitors.extend(found_urls)
        
        # If no competitors found through search, try to extract from original site
        if len(competitors) < max_results and brand_name:
            # Search for "similar to" or "alternatives to" pages
            fallback_query = f"alternatives to {brand_name} {' '.join(industry_keywords or [])}"
            fallback_urls = await self._search_google(fallback_query, max_results)
            competitors.extend(fallback_urls)
        
        # Filter and validate competitors
        validated_competitors = []
        
        for url in competitors:
            if not url:
                continue
            
            try:
                normalized_url = URLValidator.normalize_url(url)
                domain = URLValidator.get_domain(normalized_url)
                
                # Skip if we've already seen this domain
                if domain in seen_domains:
                    continue
                
                # Validate it's a Shopify store
                if await self._validate_shopify_store(normalized_url):
                    validated_competitors.append(normalized_url)
                    seen_domains.add(domain)
                    
                    if len(validated_competitors) >= max_results:
                        break
            except Exception:
                continue
        
        # If still not enough competitors, do a broader search
        if len(validated_competitors) < max_results and industry_keywords:
            broad_query = f"{industry_keywords[0]} store online shopping"
            broad_urls = await self._search_google(broad_query, max_results * 3)
            
            for url in broad_urls:
                if not url:
                    continue
                    
                try:
                    normalized_url = URLValidator.normalize_url(url)
                    domain = URLValidator.get_domain(normalized_url)
                    
                    if domain not in seen_domains:
                        if await self._validate_shopify_store(normalized_url):
                            validated_competitors.append(normalized_url)
                            seen_domains.add(domain)
                            
                            if len(validated_competitors) >= max_results:
                                break
                except Exception:
                    continue
        
        return validated_competitors[:max_results]
    
    async def _search_google(self, query: str, max_results: int) -> List[str]:
        urls = []
        
        try:
            # Clean up the query
            clean_query = query.replace('"', '').replace("'", '')
            search_url = f"https://html.duckduckgo.com/html/?q={clean_query}"
            
            if not self.session:
                timeout = aiohttp.ClientTimeout(total=15)
                self.session = aiohttp.ClientSession(timeout=timeout)
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with self.session.get(search_url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    # Extract URLs from search results
                    for link in soup.select('a.result__a'):
                        href = link.get('href')
                        if href and 'http' in href:
                            # Extract the actual URL
                            if 'uddg=' in href:
                                # DuckDuckGo redirect URL
                                import urllib.parse
                                parsed = urllib.parse.urlparse(href)
                                params = urllib.parse.parse_qs(parsed.query)
                                if 'uddg' in params:
                                    actual_url = urllib.parse.unquote(params['uddg'][0])
                                    urls.append(actual_url)
                            else:
                                urls.append(href)
                    
                    # Also try to find URLs in result snippets
                    for result in soup.select('.result__snippet'):
                        text = result.get_text()
                        # Extract URLs from text
                        url_pattern = r'https?://[^\s<>"]+'
                        found_urls = re.findall(url_pattern, text)
                        urls.extend(found_urls)
                    
        except Exception as e:
            print(f"Search error for query '{query}': {e}")
        
        # Clean and deduplicate URLs
        cleaned_urls = []
        seen = set()
        for url in urls:
            if url and url not in seen:
                # Remove trailing slashes and fragments
                clean_url = url.rstrip('/').split('#')[0]
                if clean_url and clean_url not in seen:
                    cleaned_urls.append(clean_url)
                    seen.add(clean_url)
                    if len(cleaned_urls) >= max_results:
                        break
        
        return cleaned_urls
    
    async def _validate_shopify_store(self, url: str) -> bool:
        try:
            normalized_url = URLValidator.normalize_url(url)
            
            # Quick check if it's likely an e-commerce site
            if any(keyword in normalized_url.lower() for keyword in ['shop', 'store', 'buy', 'product']):
                return True
            
            # Check if it's actually a Shopify store
            is_shopify = await ShopifyDetector.is_shopify_store(normalized_url)
            if is_shopify:
                return True
            
            # Check if /products.json exists (Shopify-specific)
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            products_url = f"{normalized_url.rstrip('/')}/products.json"
            try:
                async with self.session.get(products_url, timeout=5) as response:
                    if response.status == 200:
                        return True
            except:
                pass
            
            return False
        except Exception as e:
            print(f"Validation error for {url}: {e}")
            return False
    
    async def find_and_analyze_competitors(
        self,
        brand_name: str,
        main_brand_url: str,
        industry_keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        competitor_urls = await self.find_competitors(brand_name, industry_keywords)
        
        # Store results for later retrieval
        # In production, this would be saved to database
        return {
            'main_brand': main_brand_url,
            'competitors': competitor_urls,
            'analysis_pending': True
        }
    
    def generate_comparison_summary(
        self,
        main_insights: BrandInsights,
        competitors: List[Dict[str, Any]]
    ) -> str:
        summary_parts = []
        
        # Main brand overview
        summary_parts.append(f"Main Brand: {main_insights.brand_name or 'Unknown'}")
        summary_parts.append(f"Website: {main_insights.website_url}")
        summary_parts.append(f"Total Products: {main_insights.total_products}")
        
        if main_insights.social_handles:
            social_platforms = [s.platform for s in main_insights.social_handles]
            summary_parts.append(f"Social Presence: {', '.join(social_platforms)}")
        
        # Competitor comparison
        if competitors:
            summary_parts.append(f"\nAnalyzed {len(competitors)} Competitors:")
            
            for comp in competitors:
                summary_parts.append(f"- {comp.get('brand_name', 'Unknown')}: {comp.get('total_products', 0)} products")
            
            # Calculate averages
            avg_products = sum(c.get('statistics', {}).get('total_products', 0) for c in competitors) / len(competitors)
            summary_parts.append(f"\nAverage competitor products: {avg_products:.0f}")
            
            # Compare with main brand
            if main_insights.total_products > avg_products:
                summary_parts.append(f"Main brand has {main_insights.total_products - avg_products:.0f} more products than average")
            else:
                summary_parts.append(f"Main brand has {avg_products - main_insights.total_products:.0f} fewer products than average")
        
        return "\n".join(summary_parts)
    
    async def analyze_competitive_landscape(
        self,
        main_insights: BrandInsights,
        competitor_insights: List[BrandInsights]
    ) -> Dict[str, Any]:
        analysis = {
            'market_position': {},
            'product_comparison': {},
            'policy_comparison': {},
            'social_comparison': {},
            'recommendations': []
        }
        
        # Product comparison
        main_product_count = main_insights.total_products
        competitor_product_counts = [c.total_products for c in competitor_insights]
        avg_competitor_products = sum(competitor_product_counts) / len(competitor_product_counts) if competitor_product_counts else 0
        
        analysis['product_comparison'] = {
            'main_brand_products': main_product_count,
            'average_competitor_products': avg_competitor_products,
            'position': 'above_average' if main_product_count > avg_competitor_products else 'below_average'
        }
        
        # Policy comparison
        main_policies = sum([
            bool(main_insights.privacy_policy),
            bool(main_insights.return_refund_policy),
            bool(main_insights.shipping_policy),
            bool(main_insights.terms_of_service)
        ])
        
        competitor_policies = []
        for comp in competitor_insights:
            count = sum([
                bool(comp.privacy_policy),
                bool(comp.return_refund_policy),
                bool(comp.shipping_policy),
                bool(comp.terms_of_service)
            ])
            competitor_policies.append(count)
        
        avg_competitor_policies = sum(competitor_policies) / len(competitor_policies) if competitor_policies else 0
        
        analysis['policy_comparison'] = {
            'main_brand_policies': main_policies,
            'average_competitor_policies': avg_competitor_policies,
            'completeness': 'complete' if main_policies >= 3 else 'incomplete'
        }
        
        # Social media comparison
        main_social = len(main_insights.social_handles)
        competitor_social = [len(c.social_handles) for c in competitor_insights]
        avg_competitor_social = sum(competitor_social) / len(competitor_social) if competitor_social else 0
        
        analysis['social_comparison'] = {
            'main_brand_platforms': main_social,
            'average_competitor_platforms': avg_competitor_social,
            'presence': 'strong' if main_social >= 3 else 'weak'
        }
        
        # Generate recommendations
        if main_product_count < avg_competitor_products:
            analysis['recommendations'].append("Consider expanding product catalog to match competitor offerings")
        
        if main_policies < 3:
            analysis['recommendations'].append("Add missing policy pages to build customer trust")
        
        if main_social < avg_competitor_social:
            analysis['recommendations'].append("Increase social media presence across more platforms")
        
        if not main_insights.faqs:
            analysis['recommendations'].append("Create an FAQ section to address common customer questions")
        
        return analysis
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()