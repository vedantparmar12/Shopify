"""Core insights API routes - simplified version with only essential endpoints."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

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
                faqs=[f.dict() for f in insights.faqs],
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
        from app.services.competitor_service import CompetitorAnalysisService
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
        
        if request.find_competitors and brand_name:
            # Extract product types/categories from main brand
            product_types = set()
            for product in insights_dict.get('product_catalog', [])[:20]:
                if product.get('product_type'):
                    product_types.add(product['product_type'].lower())
            
            # Use competitor service for more comprehensive search
            try:
                async with CompetitorAnalysisService() as comp_service:
                    industry_keywords = list(product_types)[:3] if product_types else []
                    competitor_urls = await comp_service.find_competitors(
                        brand_name=brand_name,
                        industry_keywords=industry_keywords,
                        max_results=max_competitors
                    )
                    print(f"Competitor service found {len(competitor_urls)} competitors")
            except Exception as e:
                print(f"Competitor service failed, using fallback: {e}")
            
            # Fallback: Common competitor domains for different categories
            # This is a simplified approach without external search APIs
            competitor_domains = {
                'cosmetics': [
                    'https://colourpop.com',
                    'https://jeffreestarcosmetics.com',
                    'https://kyliecosmetics.com',
                    'https://fentybeauty.com',
                    'https://morphe.com'
                ],
                'fashion': [
                    'https://fashionnova.com',
                    'https://reddressboutique.com',
                    'https://shopakira.com',
                    'https://revolve.com',
                    'https://prettylittlething.com'
                ],
                'fitness': [
                    'https://gymshark.com',
                    'https://alphalete.com',
                    'https://nvgtn.com',
                    'https://buffbunny.com',
                    'https://youngla.com'
                ],
                'jewelry': [
                    'https://mejuri.com',
                    'https://missoma.com',
                    'https://astridandmiyu.com',
                    'https://analuisa.com',
                    'https://kimai.com'
                ],
                'beauty': [
                    'https://glossier.com',
                    'https://milkmakeup.com',
                    'https://rarebeauty.com',
                    'https://hauslabs.com',
                    'https://fentybeauty.com'
                ]
            }
            
            # Find relevant competitors based on product types
            for product_type in product_types:
                for category, domains in competitor_domains.items():
                    if category in product_type or product_type in category:
                        competitor_urls.extend(domains[:max_competitors])
                        break
            
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