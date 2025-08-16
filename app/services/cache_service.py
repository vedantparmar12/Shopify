"""Optional Redis cache service."""

import os
import json
import hashlib
from typing import Optional, Any, Dict
from datetime import datetime
import redis.asyncio as redis
from dotenv import load_dotenv

from app.models.brand_insights import BrandInsights

load_dotenv()


class CacheService:
    """Optional cache service - gracefully handles Redis unavailability."""
    
    def __init__(self):
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_client = None
        self.default_ttl = 3600  # 1 hour
        self.enabled = False
        
        # Try to connect to Redis but don't fail if unavailable
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=False)
            self.enabled = True
            print("Redis cache enabled")
        except Exception as e:
            print(f"Redis unavailable, caching disabled: {e}")
            self.enabled = False
    
    def _generate_cache_key(self, url: str) -> str:
        """Generate a consistent cache key from URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return f"insights:{url_hash}"
    
    async def cache_insights(
        self,
        url: str,
        insights: BrandInsights,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache insights if Redis is available."""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            cache_key = self._generate_cache_key(url)
            ttl = ttl or self.default_ttl
            
            # Convert to JSON
            insights_dict = insights.dict()
            # Convert datetime to string
            insights_dict['extraction_timestamp'] = insights_dict['extraction_timestamp'].isoformat()
            
            # Store in Redis
            await self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(insights_dict)
            )
            return True
        except Exception as e:
            print(f"Cache write error: {e}")
            return False
    
    async def get_cached_insights(self, url: str) -> Optional[BrandInsights]:
        """Get cached insights if available."""
        if not self.enabled or not self.redis_client:
            return None
        
        try:
            cache_key = self._generate_cache_key(url)
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                insights_dict = json.loads(cached_data)
                # Convert timestamp back to datetime
                if 'extraction_timestamp' in insights_dict:
                    insights_dict['extraction_timestamp'] = datetime.fromisoformat(
                        insights_dict['extraction_timestamp']
                    )
                return BrandInsights(**insights_dict)
            
            return None
        except Exception as e:
            print(f"Cache read error: {e}")
            return None
    
    async def delete_cached_insights(self, url: str) -> bool:
        """Delete cached insights."""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            cache_key = self._generate_cache_key(url)
            result = await self.redis_client.delete(cache_key)
            return result > 0
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    async def close(self):
        """Close Redis connection if exists."""
        if self.redis_client:
            await self.redis_client.close()