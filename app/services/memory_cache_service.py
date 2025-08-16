"""In-memory cache service (no Redis required)."""

import time
from typing import Optional, Dict, Any
from datetime import datetime

from app.models.enhanced_brand_insights import BrandInsights


class MemoryCacheService:
    """Simple in-memory cache service - no external dependencies."""
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = 3600  # 1 hour
        self.max_cache_size = 100  # Maximum number of cached items
        print("In-memory cache enabled")
    
    def _generate_cache_key(self, url: str) -> str:
        """Generate a consistent cache key from URL."""
        # Simple normalization
        url = url.lower().strip().rstrip('/')
        return f"insights:{url}"
    
    def _cleanup_expired(self):
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, value in self.cache.items()
            if current_time > value.get('expires_at', 0)
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def _enforce_size_limit(self):
        """Ensure cache doesn't grow too large."""
        if len(self.cache) > self.max_cache_size:
            # Remove oldest entries
            sorted_items = sorted(
                self.cache.items(),
                key=lambda x: x[1].get('created_at', 0)
            )
            # Remove oldest 20% of items
            items_to_remove = len(self.cache) - int(self.max_cache_size * 0.8)
            for key, _ in sorted_items[:items_to_remove]:
                del self.cache[key]
    
    async def cache_insights(
        self,
        url: str,
        insights: BrandInsights,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache insights in memory."""
        try:
            self._cleanup_expired()
            self._enforce_size_limit()
            
            cache_key = self._generate_cache_key(url)
            ttl = ttl or self.default_ttl
            
            self.cache[cache_key] = {
                'data': insights,
                'created_at': time.time(),
                'expires_at': time.time() + ttl
            }
            
            print(f"Cached insights for {url}")
            return True
            
        except Exception as e:
            print(f"Cache write error: {e}")
            return False
    
    async def get_cached_insights(self, url: str) -> Optional[BrandInsights]:
        """Get cached insights if available and not expired."""
        try:
            cache_key = self._generate_cache_key(url)
            
            if cache_key in self.cache:
                cache_entry = self.cache[cache_key]
                
                # Check if expired
                if time.time() > cache_entry.get('expires_at', 0):
                    del self.cache[cache_key]
                    return None
                
                print(f"Cache hit for {url}")
                return cache_entry.get('data')
            
            return None
            
        except Exception as e:
            print(f"Cache read error: {e}")
            return None
    
    async def delete_cached_insights(self, url: str) -> bool:
        """Delete cached insights."""
        try:
            cache_key = self._generate_cache_key(url)
            if cache_key in self.cache:
                del self.cache[cache_key]
                return True
            return False
            
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    async def clear_all(self):
        """Clear all cache entries."""
        self.cache.clear()
        print("Cache cleared")
    
    async def close(self):
        """No-op for compatibility."""
        pass