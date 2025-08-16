from typing import List, Dict, Any, Optional
import re
from datetime import datetime
from collections import defaultdict

from app.models.brand_insights import BrandInsights, ProductInfo
from app.services.llm_service import LLMService


class DataProcessor:
    def __init__(self):
        self.llm_service = LLMService()
    
    async def enrich_insights(self, insights: BrandInsights) -> BrandInsights:
        # Clean and structure policies using LLM if available
        if insights.privacy_policy:
            insights.privacy_policy = await self.llm_service.clean_policy_text(insights.privacy_policy)
        
        if insights.return_refund_policy:
            insights.return_refund_policy = await self.llm_service.clean_policy_text(insights.return_refund_policy)
        
        # Enrich brand context
        if not insights.brand_context and insights.brand_description:
            insights.brand_context = insights.brand_description
        
        # Deduplicate products
        insights.product_catalog = self._deduplicate_products(insights.product_catalog)
        insights.hero_products = self._deduplicate_products(insights.hero_products)
        
        # Ensure hero products are unique and not in main catalog
        hero_names = {p.name.lower() for p in insights.hero_products}
        insights.product_catalog = [
            p for p in insights.product_catalog 
            if p.name.lower() not in hero_names
        ]
        
        # Add product statistics
        insights.total_products = len(insights.product_catalog) + len(insights.hero_products)
        
        # Clean contact info
        insights.contact_info.emails = self._clean_emails(insights.contact_info.emails)
        insights.contact_info.phone_numbers = self._clean_phone_numbers(insights.contact_info.phone_numbers)
        
        # Deduplicate social handles
        insights.social_handles = self._deduplicate_social_handles(insights.social_handles)
        
        # Deduplicate important links
        insights.important_links = self._deduplicate_links(insights.important_links)
        
        return insights
    
    def _deduplicate_products(self, products: List[ProductInfo]) -> List[ProductInfo]:
        seen = set()
        unique_products = []
        
        for product in products:
            key = product.name.lower().strip()
            if key not in seen:
                seen.add(key)
                unique_products.append(product)
        
        return unique_products
    
    def _clean_emails(self, emails: List[str]) -> List[str]:
        cleaned = []
        seen = set()
        
        for email in emails:
            email = email.lower().strip()
            # Filter out common placeholder emails
            if email not in seen and not any(x in email for x in ['example.com', 'test.com', 'yourstore.com']):
                seen.add(email)
                cleaned.append(email)
        
        return cleaned[:3]  # Keep top 3
    
    def _clean_phone_numbers(self, phones: List[str]) -> List[str]:
        cleaned = []
        seen = set()
        
        for phone in phones:
            # Remove all non-digit characters for comparison
            digits_only = re.sub(r'\D', '', phone)
            if digits_only not in seen and len(digits_only) >= 10:
                seen.add(digits_only)
                cleaned.append(phone)
        
        return cleaned[:3]  # Keep top 3
    
    def _deduplicate_social_handles(self, handles: List) -> List:
        seen = set()
        unique = []
        
        for handle in handles:
            key = f"{handle.platform}:{handle.url}"
            if key not in seen:
                seen.add(key)
                unique.append(handle)
        
        return unique
    
    def _deduplicate_links(self, links: List) -> List:
        seen = set()
        unique = []
        
        for link in links:
            if str(link.url) not in seen:
                seen.add(str(link.url))
                unique.append(link)
        
        return unique[:15]  # Keep top 15
    
    def calculate_extraction_quality_score(self, insights: BrandInsights) -> float:
        score = 0.0
        max_score = 100.0
        
        # Product catalog (20 points)
        if insights.product_catalog:
            score += min(20, len(insights.product_catalog) * 0.5)
        
        # Hero products (10 points)
        if insights.hero_products:
            score += min(10, len(insights.hero_products) * 2)
        
        # Policies (20 points total, 5 each)
        if insights.privacy_policy:
            score += 5
        if insights.return_refund_policy:
            score += 5
        if insights.shipping_policy:
            score += 5
        if insights.terms_of_service:
            score += 5
        
        # FAQs (10 points)
        if insights.faqs:
            score += min(10, len(insights.faqs))
        
        # Brand context (10 points)
        if insights.brand_context:
            score += 10
        
        # Social handles (10 points)
        if insights.social_handles:
            score += min(10, len(insights.social_handles) * 2)
        
        # Contact info (10 points)
        if insights.contact_info.emails:
            score += 5
        if insights.contact_info.phone_numbers:
            score += 5
        
        # Important links (10 points)
        if insights.important_links:
            score += min(10, len(insights.important_links))
        
        return round(score / max_score * 100, 2)
    
    def generate_extraction_summary(self, insights: BrandInsights) -> Dict[str, Any]:
        quality_score = self.calculate_extraction_quality_score(insights)
        
        summary = {
            'brand_name': insights.brand_name,
            'website_url': str(insights.website_url),
            'extraction_timestamp': insights.extraction_timestamp.isoformat(),
            'extraction_success': insights.extraction_success,
            'quality_score': quality_score,
            'statistics': {
                'total_products': insights.total_products,
                'hero_products_count': len(insights.hero_products),
                'faqs_count': len(insights.faqs),
                'social_platforms_count': len(insights.social_handles),
                'policies_extracted': sum([
                    bool(insights.privacy_policy),
                    bool(insights.return_refund_policy),
                    bool(insights.shipping_policy),
                    bool(insights.terms_of_service)
                ]),
                'contact_methods': sum([
                    bool(insights.contact_info.emails),
                    bool(insights.contact_info.phone_numbers),
                    bool(insights.contact_info.address)
                ])
            },
            'extraction_duration_seconds': insights.extraction_duration_seconds,
            'errors': insights.error_messages
        }
        
        return summary
    
    def filter_insights_by_criteria(
        self, 
        insights: BrandInsights, 
        include_products: bool = True,
        include_policies: bool = True,
        include_faqs: bool = True,
        include_social: bool = True,
        max_products: Optional[int] = None
    ) -> Dict[str, Any]:
        
        filtered = {
            'website_url': str(insights.website_url),
            'brand_name': insights.brand_name,
            'extraction_timestamp': insights.extraction_timestamp.isoformat()
        }
        
        if include_products:
            products = insights.product_catalog[:max_products] if max_products else insights.product_catalog
            filtered['products'] = [p.dict() for p in products]
            filtered['hero_products'] = [p.dict() for p in insights.hero_products]
        
        if include_policies:
            filtered['policies'] = {
                'privacy_policy': insights.privacy_policy,
                'return_refund_policy': insights.return_refund_policy,
                'shipping_policy': insights.shipping_policy,
                'terms_of_service': insights.terms_of_service
            }
        
        if include_faqs:
            filtered['faqs'] = [faq.dict() for faq in insights.faqs]
        
        if include_social:
            filtered['social_handles'] = [s.dict() for s in insights.social_handles]
            filtered['contact_info'] = insights.contact_info.dict()
        
        return filtered