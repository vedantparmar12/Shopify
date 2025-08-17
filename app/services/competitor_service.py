import asyncio
import aiohttp
from typing import List, Optional, Dict, Any
import json
import re

from app.models.brand_insights import BrandInsights
from app.services.llm_service import LLMService


class CompetitorAnalysisService:
    def __init__(self):
        self.session = None
        self.llm_service = LLMService()
    
    async def find_competitors(
        self,
        brand_name: str,
        industry_keywords: Optional[List[str]] = None,
        max_results: int = 5
    ) -> List[str]:
        """
        Find competitors quickly using LLM only.
        Much faster approach without URL validation.
        """
        competitors = []
        
        print(f"Finding competitors for: {brand_name}")
        print(f"Industry keywords: {industry_keywords}")
        
        # Use LLM to suggest competitors (fast approach)
        if self.llm_service.use_llm:
            competitors = await self._get_llm_competitors(
                brand_name, industry_keywords, max_results
            )
        
        # If no LLM or no results, return some default suggestions based on industry
        if not competitors and industry_keywords:
            competitors = await self._get_industry_defaults(industry_keywords, max_results)
        
        return competitors[:max_results]
    
    async def _get_llm_competitors(
        self, 
        brand_name: str, 
        industry_keywords: Optional[List[str]],
        max_results: int
    ) -> List[str]:
        """Use LLM to suggest competitor websites quickly."""
        if not self.llm_service.use_llm:
            return []
        
        # Build context
        industry_context = ""
        if industry_keywords:
            industry_context = f"Industry/Category: {', '.join(industry_keywords[:3])}"
        
        prompt = f"""
        List {max_results} competitor e-commerce websites for {brand_name}.
        {industry_context}
        
        Requirements:
        - Return actual online stores that sell similar products
        - Include the full website URL
        - Focus on popular, well-known brands
        
        Return ONLY a JSON array of URLs, nothing else:
        ["https://example1.com", "https://example2.com", ...]
        """
        
        try:
            response = await self.llm_service._call_llm(prompt)
            
            # Clean response
            response = response.strip()
            if '```' in response:
                # Extract content between backticks
                parts = response.split('```')
                for part in parts:
                    if '[' in part and ']' in part:
                        response = part
                        break
            
            if response.startswith('json'):
                response = response[4:].strip()
            
            # Extract URLs
            urls = []
            
            # Try JSON parsing first
            try:
                parsed = json.loads(response)
                if isinstance(parsed, list):
                    urls = [str(url) for url in parsed if url and isinstance(url, str)]
            except:
                # Fallback: extract URLs with regex
                url_pattern = r'https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}'
                found_urls = re.findall(url_pattern, response)
                urls = found_urls
            
            # Clean URLs
            cleaned_urls = []
            for url in urls:
                if url and url.startswith('http'):
                    # Remove trailing slashes and clean
                    url = url.rstrip('/')
                    if 'example' not in url.lower():  # Filter out example URLs
                        cleaned_urls.append(url)
            
            print(f"LLM suggested {len(cleaned_urls)} competitors")
            return cleaned_urls
            
        except Exception as e:
            print(f"LLM competitor suggestion failed: {e}")
            return []
    
    async def _get_industry_defaults(
        self,
        industry_keywords: List[str],
        max_results: int
    ) -> List[str]:
        """Get default competitors based on industry keywords."""
        if not industry_keywords:
            return []
        
        # Determine industry from keywords
        keywords_text = ' '.join(industry_keywords).lower()
        
        # Use LLM to get industry leaders if available
        if self.llm_service.use_llm:
            industry = self._determine_industry(keywords_text)
            
            prompt = f"""
            List the top {max_results} popular e-commerce websites that sell {industry} products.
            Focus on well-known brands with online stores.
            
            Return ONLY a JSON array of URLs:
            ["https://example1.com", "https://example2.com", ...]
            """
            
            try:
                response = await self.llm_service._call_llm(prompt)
                
                # Parse response
                response = response.strip()
                if '```' in response:
                    parts = response.split('```')
                    for part in parts:
                        if '[' in part and ']' in part:
                            response = part
                            break
                
                urls = []
                try:
                    parsed = json.loads(response)
                    if isinstance(parsed, list):
                        urls = [str(url) for url in parsed if url and 'example' not in str(url).lower()]
                except:
                    url_pattern = r'https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}'
                    urls = re.findall(url_pattern, response)
                
                return urls[:max_results]
            except:
                pass
        
        return []
    
    def _determine_industry(self, keywords_text: str) -> str:
        """Determine industry from keywords."""
        keywords_lower = keywords_text.lower()
        
        if any(word in keywords_lower for word in ['cosmetic', 'makeup', 'lipstick', 'foundation']):
            return "cosmetics and makeup"
        elif any(word in keywords_lower for word in ['fashion', 'clothing', 'apparel', 'dress']):
            return "fashion and clothing"
        elif any(word in keywords_lower for word in ['jewelry', 'jewellery', 'ring', 'necklace']):
            return "jewelry and accessories"
        elif any(word in keywords_lower for word in ['fitness', 'gym', 'athletic', 'sportswear']):
            return "fitness and sportswear"
        elif any(word in keywords_lower for word in ['beauty', 'skincare', 'serum', 'moisturizer']):
            return "beauty and skincare"
        elif any(word in keywords_lower for word in ['home', 'furniture', 'decor', 'kitchen']):
            return "home and decor"
        elif any(word in keywords_lower for word in ['electronic', 'gadget', 'tech', 'device']):
            return "electronics and gadgets"
        elif any(word in keywords_lower for word in ['bag', 'purse', 'wallet', 'accessory']):
            return "bags and accessories"
        else:
            return "general retail"
    
    def generate_comparison_summary(
        self,
        main_insights: BrandInsights,
        competitors: List[Dict[str, Any]]
    ) -> str:
        """Generate a summary of the competitive analysis."""
        summary = []
        
        summary.append(f"Main Brand: {main_insights.brand_name or 'Unknown'}")
        summary.append(f"Website: {main_insights.website_url}")
        summary.append(f"Products: {main_insights.total_products}")
        
        if competitors:
            summary.append(f"\nFound {len(competitors)} Competitors")
            for comp in competitors:
                if isinstance(comp, dict):
                    name = comp.get('brand_name', comp.get('website_url', 'Unknown'))
                    summary.append(f"- {name}")
                else:
                    summary.append(f"- {comp}")
        
        return "\n".join(summary)
    
    async def analyze_competitive_landscape(
        self,
        main_insights: BrandInsights,
        competitor_insights: List[BrandInsights]
    ) -> Dict[str, Any]:
        """Analyze competitive positioning."""
        analysis = {
            'market_position': {},
            'product_comparison': {},
            'recommendations': []
        }
        
        if competitor_insights:
            main_products = main_insights.total_products
            comp_products = [c.total_products for c in competitor_insights if hasattr(c, 'total_products')]
            
            if comp_products:
                avg_products = sum(comp_products) / len(comp_products)
                analysis['product_comparison'] = {
                    'main_brand': main_products,
                    'average_competitors': avg_products,
                    'position': 'above average' if main_products > avg_products else 'below average'
                }
        
        return analysis
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()