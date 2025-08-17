import asyncio
import aiohttp
import json
import os
import duckdb
from typing import List, Optional, Dict, Any
from pathlib import Path

class FastCompetitorService:
    def __init__(self):
        self.session = None
        self.db_path = Path("data/competitors.duckdb")
        self.db_path.parent.mkdir(exist_ok=True)
        self.conn = None
        self._init_database()
        
        # API keys for search services
        self.serpapi_key = os.getenv('SERPAPI_KEY')
        self.google_cse_id = os.getenv('GOOGLE_CSE_ID')
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
    
    def _init_database(self):
        try:
            self.conn = duckdb.connect(str(self.db_path))
            
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS competitors (
                    brand_name VARCHAR,
                    domain VARCHAR,
                    industry VARCHAR,
                    competitor_domains VARCHAR[],
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS industry_leaders (
                    industry VARCHAR PRIMARY KEY,
                    top_brands VARCHAR[],
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self._populate_industry_leaders()
        except Exception as e:
            print(f"Failed to initialize DuckDB: {e}")
            self.conn = None
    
    def _populate_industry_leaders(self):
        if not self.conn:
            return
            
        industry_data = {
            'cosmetics': ['sephora.com', 'ulta.com', 'colourpop.com', 'glossier.com', 'kyliecosmetics.com'],
            'fashion': ['zara.com', 'hm.com', 'forever21.com', 'asos.com', 'shein.com'],
            'jewelry': ['tiffany.com', 'pandora.net', 'bluenile.com', 'jamesallen.com', 'mejuri.com'],
            'electronics': ['bestbuy.com', 'newegg.com', 'bhphotovideo.com', 'adorama.com', 'microcenter.com'],
            'home': ['ikea.com', 'wayfair.com', 'overstock.com', 'cb2.com', 'westelm.com'],
            'sports': ['nike.com', 'adidas.com', 'underarmour.com', 'puma.com', 'reebok.com'],
            'beauty': ['sephora.com', 'ulta.com', 'glossier.com', 'fenty.com', 'beautybay.com']
        }
        
        for industry, brands in industry_data.items():
            try:
                self.conn.execute("""
                    INSERT OR REPLACE INTO industry_leaders (industry, top_brands)
                    VALUES (?, ?)
                """, [industry, brands])
            except:
                pass
    
    async def find_competitors(
        self,
        brand_name: str,
        domain: str = None,
        industry: str = None,
        max_results: int = 5
    ) -> List[str]:
        try:
            return await asyncio.wait_for(
                self._find_competitors_internal(brand_name, domain, industry, max_results),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            print(f"Competitor search timed out after 5 seconds")
            if industry:
                return self._get_fallback_industry_leaders(industry)[:max_results]
            return []
    
    async def _find_competitors_internal(
        self,
        brand_name: str,
        domain: str = None,
        industry: str = None,
        max_results: int = 5
    ) -> List[str]:
        competitors = []
        
        if domain:
            cached = self._get_cached_competitors(domain)
            if cached:
                return cached[:max_results]
        
        if industry:
            leaders = self._get_industry_leaders(industry)
            if leaders:
                competitors.extend(leaders)
        
        if len(competitors) < max_results:
            if self.serpapi_key:
                api_results = await self._search_serpapi(brand_name, industry)
                competitors.extend(api_results)
            elif self.google_api_key and self.google_cse_id:
                api_results = await self._search_google_cse(brand_name, industry)
                competitors.extend(api_results)
        
        if len(competitors) < max_results:
            quick_results = await self._quick_search(brand_name, industry)
            competitors.extend(quick_results)
        
        seen = set()
        unique_competitors = []
        for comp in competitors:
            if comp and comp not in seen:
                seen.add(comp)
                unique_competitors.append(comp)
                if len(unique_competitors) >= max_results:
                    break
        
        if domain and unique_competitors:
            self._cache_competitors(domain, brand_name, industry, unique_competitors)
        
        return unique_competitors[:max_results]
    
    def _get_cached_competitors(self, domain: str) -> List[str]:
        if not self.conn:
            return []
            
        try:
            result = self.conn.execute("""
                SELECT competitor_domains 
                FROM competitors 
                WHERE domain = ?
                LIMIT 1
            """, [domain]).fetchone()
            
            if result and result[0]:
                return result[0]
        except:
            pass
        return []
    
    def _get_industry_leaders(self, industry: str) -> List[str]:
        if not self.conn:
            return self._get_fallback_industry_leaders(industry)
            
        try:
            industry_lower = industry.lower()
            
            result = self.conn.execute("""
                SELECT top_brands 
                FROM industry_leaders 
                WHERE industry = ?
                LIMIT 1
            """, [industry_lower]).fetchone()
            
            if result and result[0]:
                return [f"https://{domain}" for domain in result[0]]
            
            result = self.conn.execute("""
                SELECT top_brands 
                FROM industry_leaders 
                WHERE industry LIKE ?
                LIMIT 1
            """, [f"%{industry_lower.split()[0]}%"]).fetchone()
            
            if result and result[0]:
                return [f"https://{domain}" for domain in result[0]]
        except:
            pass
        return self._get_fallback_industry_leaders(industry)
    
    def _get_fallback_industry_leaders(self, industry: str) -> List[str]:
        industry_lower = industry.lower() if industry else ""
        
        if 'cosmetic' in industry_lower or 'makeup' in industry_lower:
            return ['https://sephora.com', 'https://ulta.com', 'https://colourpop.com']
        elif 'fashion' in industry_lower or 'clothing' in industry_lower:
            return ['https://zara.com', 'https://hm.com', 'https://asos.com']
        elif 'jewelry' in industry_lower:
            return ['https://tiffany.com', 'https://pandora.net', 'https://mejuri.com']
        elif 'beauty' in industry_lower or 'skincare' in industry_lower:
            return ['https://sephora.com', 'https://glossier.com', 'https://fenty.com']
        else:
            return []
    
    def _cache_competitors(
        self, 
        domain: str, 
        brand_name: str, 
        industry: str, 
        competitors: List[str]
    ):
        if not self.conn:
            return
            
        try:
            comp_domains = []
            for comp in competitors:
                if '://' in comp:
                    comp_domain = comp.split('://')[1].split('/')[0]
                else:
                    comp_domain = comp
                comp_domains.append(comp_domain)
            
            self.conn.execute("""
                INSERT OR REPLACE INTO competitors 
                (brand_name, domain, industry, competitor_domains)
                VALUES (?, ?, ?, ?)
            """, [brand_name, domain, industry, comp_domains])
        except:
            pass
    
    async def _search_serpapi(self, brand_name: str, industry: str = None) -> List[str]:
        if not self.serpapi_key:
            return []
        
        try:
            query = f"{brand_name} competitors alternatives online stores"
            if industry:
                query = f"{industry} stores like {brand_name}"
            
            url = "https://serpapi.com/search"
            params = {
                'q': query,
                'api_key': self.serpapi_key,
                'engine': 'google',
                'num': 10
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3))
            
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=3)) as response:
                if response.status == 200:
                    data = await response.json()
                    urls = []
                    
                    for result in data.get('organic_results', [])[:10]:
                        link = result.get('link')
                        if link and self._is_valid_competitor_url(link):
                            urls.append(link)
                    
                    return urls
        except:
            pass
        return []
    
    async def _search_google_cse(self, brand_name: str, industry: str = None) -> List[str]:
        if not (self.google_api_key and self.google_cse_id):
            return []
        
        try:
            query = f"{brand_name} competitors similar stores"
            if industry:
                query = f"{industry} online stores like {brand_name}"
            
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.google_api_key,
                'cx': self.google_cse_id,
                'q': query,
                'num': 10
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3))
            
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=3)) as response:
                if response.status == 200:
                    data = await response.json()
                    urls = []
                    
                    for item in data.get('items', [])[:10]:
                        link = item.get('link')
                        if link and self._is_valid_competitor_url(link):
                            urls.append(link)
                    
                    return urls
        except:
            pass
        return []
    
    async def _quick_search(self, brand_name: str, industry: str = None) -> List[str]:
        return []
    
    def _is_valid_competitor_url(self, url: str) -> bool:
        if not url or not url.startswith('http'):
            return False
        
        excluded = ['wikipedia', 'facebook', 'twitter', 'instagram', 'youtube', 
                   'amazon', 'ebay', 'google', 'bing', 'reddit', 'pinterest']
        
        url_lower = url.lower()
        return not any(exc in url_lower for exc in excluded)
    
    def close(self):
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
        if self.session:
            asyncio.create_task(self.session.close())
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()