from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio

router = APIRouter(prefix="/api/version1", tags=["Core Insights"])


class ExtractRequest(BaseModel):
    """Request model for extraction."""
    website_url: str


class CompetitorRequest(BaseModel):
    """Request model for competitor analysis."""
    website_url: str
    find_competitors: bool = True
    max_competitors: int = 5


class BrandInsights(BaseModel):
    """Core brand insights response model."""
    website_url: str
    brand_name: Optional[str] = None
    
    # Products
    product_catalog: List[Dict[str, Any]] = []
    hero_products: List[Dict[str, Any]] = []
    total_products: int = 0
    
    # Policies
    privacy_policy: Optional[str] = None
    return_refund_policy: Optional[str] = None
    shipping_policy: Optional[str] = None
    terms_of_service: Optional[str] = None
    
    # Brand Information
    brand_context: Optional[str] = None
    faqs: List[Dict[str, str]] = []
    
    # Contact & Social
    social_handles: List[Dict[str, str]] = []
    contact_info: Dict[str, Any] = {}
    important_links: List[Dict[str, str]] = []
    
    # Metadata
    extraction_timestamp: str
    extraction_success: bool = True
    error_messages: List[str] = []
    quality_score: int = 0


class CompetitorAnalysis(BaseModel):
    """Competitor analysis response model."""
    main_brand_url: str
    main_brand_name: Optional[str] = None
    competitors_found: int = 0
    competitor_urls: List[str] = []
    competitor_insights: Optional[List[Dict[str, Any]]] = None
    analysis_timestamp: str


@router.post("/extract", response_model=BrandInsights)
async def extract_brand_insights(request: ExtractRequest):
    """
    Extract comprehensive brand insights from a Shopify store.
    
    This endpoint extracts all 9 mandatory data points:
    1. Brand name (from meta tags, domain, etc.)
    2. Product catalog (from /products.json with pagination)
    3. Hero/featured products (from homepage)
    4. Privacy policy
    5. Return/refund policy
    6. FAQs (filtered, no navigation items)
    7. Social media handles
    8. Contact information (emails, phones with tel: support)
    9. Brand context/about information
    
    Features:
    - Enhanced brand name extraction
    - FAQ filtering (removes navigation items)
    - Phone number detection including tel: links
    - Product pagination support
    - Quality scoring
    
    Returns:
    - 200: Successfully extracted insights
    - 404: Website not found
    - 500: Internal server error
    """
    
    website_url = request.website_url
    
    try:
        print(f"Extracting insights from: {website_url}")
        
        # Import the working scraper service
        from app.services.working_scraper import WorkingShopifyScraperService
        from app.services.data_processor import DataProcessor
        from app.database.service import DatabaseService
        
        # Extract insights
        async with WorkingShopifyScraperService() as scraper:
            insights = await scraper.extract_insights(website_url)
        
        # Enrich insights if it's a BrandInsights object
        if hasattr(insights, 'brand_name'):
            # It's already a BrandInsights object
            data_processor = DataProcessor()
            insights = await data_processor.enrich_insights(insights)
            
            # Save to database (bonus feature)
            try:
                db_service = DatabaseService()
                if db_service.enabled:
                    await db_service.save_insights(insights)
                    print(f"Saved insights to database for {website_url}")
            except Exception as e:
                print(f"Failed to save to database: {e}")
            
            # Convert to response format with proper URL handling
            def convert_url(url):
                if url is None:
                    return None
                return str(url) if hasattr(url, '__str__') else url
            
            # Process products with URL conversion
            product_catalog = []
            for p in insights.product_catalog:
                prod_dict = p.dict()
                if 'image_url' in prod_dict:
                    prod_dict['image_url'] = convert_url(prod_dict.get('image_url'))
                if 'product_url' in prod_dict:
                    prod_dict['product_url'] = convert_url(prod_dict.get('product_url'))
                product_catalog.append(prod_dict)
            
            hero_products = []
            for p in insights.hero_products:
                prod_dict = p.dict()
                if 'image_url' in prod_dict:
                    prod_dict['image_url'] = convert_url(prod_dict.get('image_url'))
                if 'product_url' in prod_dict:
                    prod_dict['product_url'] = convert_url(prod_dict.get('product_url'))
                hero_products.append(prod_dict)
            
            # Process social handles with URL conversion
            social_handles = []
            for s in insights.social_handles:
                social_dict = s.dict()
                social_dict['url'] = convert_url(social_dict.get('url'))
                social_handles.append(social_dict)
            
            # Process important links with URL conversion
            important_links = []
            for l in insights.important_links:
                link_dict = l.dict()
                link_dict['url'] = convert_url(link_dict.get('url'))
                important_links.append(link_dict)
            
            return BrandInsights(
                website_url=str(insights.website_url),
                brand_name=insights.brand_name,
                product_catalog=product_catalog,
                hero_products=hero_products,
                total_products=insights.total_products,
                privacy_policy=insights.privacy_policy,
                return_refund_policy=insights.return_refund_policy,
                shipping_policy=insights.shipping_policy,
                terms_of_service=insights.terms_of_service,
                brand_context=insights.brand_context,
                faqs=[{
                    'question': f.question,
                    'answer': f.answer,
                    'category': f.category or 'General'
                } for f in insights.faqs],
                social_handles=social_handles,
                contact_info=insights.contact_info.dict(),
                important_links=important_links,
                extraction_timestamp=insights.extraction_timestamp.isoformat(),
                extraction_success=insights.extraction_success,
                error_messages=insights.error_messages,
                quality_score=0
            )
        else:
            # It's a dictionary, convert to BrandInsights
            response = BrandInsights(
                website_url=insights.get('website_url', website_url),
                brand_name=insights.get('brand_name'),
                product_catalog=insights.get('product_catalog', []),
                hero_products=insights.get('hero_products', []),
                total_products=insights.get('total_products', 0),
                privacy_policy=insights.get('privacy_policy'),
                return_refund_policy=insights.get('return_refund_policy'),
                shipping_policy=insights.get('shipping_policy'),
                terms_of_service=insights.get('terms_of_service'),
                brand_context=insights.get('brand_context'),
                faqs=insights.get('faqs', []),
                social_handles=insights.get('social_handles', []),
                contact_info=insights.get('contact_info', {}),
                important_links=insights.get('important_links', []),
                extraction_timestamp=datetime.utcnow().isoformat(),
                extraction_success=True,
                error_messages=[],
                quality_score=insights.get('quality_score', 0)
            )
            return response
        
    except Exception as e:
        print(f"Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Return partial results with error
        return BrandInsights(
            website_url=website_url,
            extraction_success=False,
            error_messages=[str(e)],
            extraction_timestamp=datetime.utcnow().isoformat()
        )


@router.post("/competitors", response_model=CompetitorAnalysis)
async def analyze_competitors(request: CompetitorRequest):
    """
    Find and analyze competitors for a given Shopify store.
    
    Features:
    - Discovers competitors beyond just myshopify.com domains
    - Searches multiple sources for competitor identification
    - Can extract basic insights from competitor stores
    - Returns competitor URLs and optional analysis
    
    Parameters:
    - website_url: The main brand's website URL
    - find_competitors: Whether to search for competitors (default: true)
    - max_competitors: Maximum number of competitors to find (default: 5)
    
    Returns:
    - 200: Successfully found competitors
    - 500: Internal server error
    """
    
    website_url = request.website_url
    max_competitors = min(request.max_competitors, 10)  # Cap at 10
    
    try:
        print(f"Finding competitors for: {website_url}")
        
        # First extract brand insights to get brand name
        from app.services.working_scraper import WorkingShopifyScraperService
        from app.services.fast_competitor_service import FastCompetitorService
        from app.database.service import DatabaseService
        
        async with WorkingShopifyScraperService() as scraper:
            main_insights = await scraper.extract_insights(website_url)
        
        # Convert BrandInsights object to dict if needed
        if hasattr(main_insights, 'brand_name'):
            brand_name = main_insights.brand_name or ''
            # Convert to dict for product access
            insights_dict = {
                'brand_name': main_insights.brand_name,
                'product_catalog': [{
                    'product_type': getattr(p, 'product_type', None)
                } for p in (main_insights.product_catalog or [])]
            }
        else:
            brand_name = main_insights.get('brand_name', '')
            insights_dict = main_insights
        
        # Use CompetitorAnalysisService for enhanced competitor discovery
        competitor_urls = []
        
        if request.find_competitors:
            # Extract product types/categories from main brand
            product_types = set()
            products = []
            
            # Handle both BrandInsights object and dict
            if hasattr(main_insights, 'product_catalog'):
                products = main_insights.product_catalog or []
            else:
                products = insights_dict.get('product_catalog', [])
            
            # Get product types and names for industry detection
            product_names = []
            for product in products[:20]:
                if hasattr(product, 'product_type') and product.product_type:
                    product_types.add(product.product_type.lower())
                elif isinstance(product, dict) and product.get('product_type'):
                    product_types.add(product['product_type'].lower())
                
                # Also collect product names for better industry detection
                if hasattr(product, 'name'):
                    product_names.append(product.name.lower())
                elif isinstance(product, dict) and product.get('name'):
                    product_names.append(product['name'].lower())
            
            # Determine industry from product names and types
            industry_keywords = list(product_types)[:3] if product_types else []
            
            # If no product types, try to infer from product names
            if not industry_keywords and product_names:
                # Common industry keywords to look for in product names
                industry_patterns = {
                    'cosmetics': ['lipstick', 'foundation', 'mascara', 'eyeshadow', 'makeup', 'cosmetic'],
                    'fashion': ['dress', 'shirt', 'pants', 'jacket', 'clothing', 'apparel'],
                    'jewelry': ['ring', 'necklace', 'bracelet', 'earring', 'pendant'],
                    'beauty': ['serum', 'cream', 'moisturizer', 'cleanser', 'skincare'],
                    'accessories': ['bag', 'wallet', 'belt', 'hat', 'scarf']
                }
                
                products_text = ' '.join(product_names)
                for industry, patterns in industry_patterns.items():
                    if any(pattern in products_text for pattern in patterns):
                        industry_keywords = [industry]
                        break
            
            print(f"Detected industry keywords: {industry_keywords}")
            
            # Use FAST competitor service with DuckDB
            try:
                # Determine industry from keywords
                industry = None
                if industry_keywords:
                    keywords_text = ' '.join(industry_keywords).lower()
                    if 'cosmetic' in keywords_text or 'makeup' in keywords_text:
                        industry = 'cosmetics'
                    elif 'fashion' in keywords_text or 'clothing' in keywords_text:
                        industry = 'fashion'
                    elif 'jewelry' in keywords_text or 'jewellery' in keywords_text:
                        industry = 'jewelry'
                    elif 'electronic' in keywords_text or 'tech' in keywords_text:
                        industry = 'electronics'
                    elif 'home' in keywords_text or 'furniture' in keywords_text:
                        industry = 'home'
                    elif 'sport' in keywords_text or 'fitness' in keywords_text:
                        industry = 'sports'
                    elif 'beauty' in keywords_text or 'skincare' in keywords_text:
                        industry = 'beauty'
                
                # Extract domain from URL
                from urllib.parse import urlparse
                parsed_url = urlparse(website_url)
                domain = parsed_url.netloc
                
                # Use fast competitor service
                async with FastCompetitorService() as comp_service:
                    competitor_urls = await comp_service.find_competitors(
                        brand_name=brand_name or domain,
                        domain=domain,
                        industry=industry,
                        max_results=max_competitors
                    )
                    print(f"Fast competitor service found {len(competitor_urls)} competitors instantly")
            except Exception as e:
                print(f"Fast competitor service failed: {e}")
                competitor_urls = []
            
            # No hardcoded fallback - competitors must be found dynamically
            if not competitor_urls:
                print("No competitors found through search or LLM")
            
            # Remove the main brand URL if it's in the list
            competitor_urls = [url for url in competitor_urls if url != website_url]
            
            # Limit to requested number
            competitor_urls = competitor_urls[:max_competitors]
        
        # Optionally extract insights from competitors
        competitor_insights = None
        if competitor_urls and request.find_competitors:
            competitor_insights = []
            for comp_url in competitor_urls[:3]:  # Limit to 3 for performance
                try:
                    async with WorkingShopifyScraperService() as scraper:
                        comp_insight = await scraper.extract_insights(comp_url)
                        if hasattr(comp_insight, 'brand_name'):
                            competitor_insights.append({
                                'website_url': comp_url,
                                'brand_name': comp_insight.brand_name,
                                'total_products': comp_insight.total_products,
                                'has_faqs': bool(comp_insight.faqs),
                                'social_platforms': len(comp_insight.social_handles)
                            })
                except Exception as e:
                    print(f"Failed to analyze competitor {comp_url}: {e}")
        
        # Save competitor analysis to database (bonus feature)
        try:
            db_service = DatabaseService()
            if db_service.enabled and competitor_urls:
                await db_service.save_competitor_analysis(
                    main_brand_url=website_url,
                    main_brand_name=brand_name,
                    competitors=competitor_insights or [],
                    analysis_summary=f"Found {len(competitor_urls)} competitors",
                    industry_keywords=list(product_types)[:5] if 'product_types' in locals() else None
                )
                print(f"Saved competitor analysis to database")
        except Exception as e:
            print(f"Failed to save competitor analysis: {e}")
        
        # Build response
        response = CompetitorAnalysis(
            main_brand_url=website_url,
            main_brand_name=brand_name,
            competitors_found=len(competitor_urls),
            competitor_urls=competitor_urls,
            competitor_insights=competitor_insights,
            analysis_timestamp=datetime.utcnow().isoformat()
        )
        
        print(f"Found {len(competitor_urls)} competitors for {brand_name or website_url}")
        return response
        
    except Exception as e:
        print(f"Competitor analysis failed: {e}")
        
        return CompetitorAnalysis(
            main_brand_url=website_url,
            competitors_found=0,
            competitor_urls=[],
            analysis_timestamp=datetime.utcnow().isoformat()
        )
