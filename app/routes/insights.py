from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import HttpUrl
from typing import Optional

from app.models.brand_insights import BrandInsights
from app.models.response_models import CompetitorAnalysisRequest, CompetitorAnalysisResponse
from app.services.simple_scraper import SimpleShopifyScraperService as ShopifyScraperService
from app.services.data_processor import DataProcessor
from app.services.competitor_service import CompetitorAnalysisService
from app.database.service import DatabaseService
from app.utils.validators import URLValidator
from app.utils.exceptions import InsightsAPIException

router = APIRouter(prefix="/api/v1", tags=["insights"])

data_processor = DataProcessor()
db_service = DatabaseService()
competitor_service = CompetitorAnalysisService()


@router.post("/extract", response_model=BrandInsights)
async def extract_brand_insights(
    website_url: HttpUrl,
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> BrandInsights:
    """
    Extract comprehensive brand insights from a Shopify store.
    
    Required data points:
    1. Whole Product Catalog
    2. Hero Products (Homepage products)
    3. Privacy Policy
    4. Return/Refund Policies
    5. Brand FAQs
    6. Social Handles
    7. Contact Details
    8. Brand Context (About)
    9. Important Links
    
    Args:
        website_url: The Shopify store URL to analyze
        
    Returns:
        BrandInsights object with all extracted data
        
    Raises:
        401: Website not found
        500: Internal server error
    """
    normalized_url = URLValidator.normalize_url(str(website_url))
    
    try:
        async with ShopifyScraperService() as scraper:
            insights = await scraper.extract_insights(normalized_url)
        
        insights = await data_processor.enrich_insights(insights)
        
        background_tasks.add_task(db_service.save_insights, insights)
        
        return insights
    
    except InsightsAPIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        import traceback
        print(f"Error extracting insights: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/competitors", response_model=CompetitorAnalysisResponse)
async def analyze_competitors(
    request: CompetitorAnalysisRequest,
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> CompetitorAnalysisResponse:
    """
    BONUS FEATURE: Analyze competitors of a given brand.
    
    Finds competitors and extracts the same insights from their stores.
    
    Args:
        request: Contains website URL and competitor analysis parameters
        
    Returns:
        Analysis of main brand and its competitors
    """
    try:
        # Normalize URL first
        normalized_url = URLValidator.normalize_url(str(request.website_url))
        
        async with ShopifyScraperService() as scraper:
            main_insights = await scraper.extract_insights(normalized_url)
            main_insights = await data_processor.enrich_insights(main_insights)
        
        competitors = []
        if request.find_competitors:
            competitor_urls = await competitor_service.find_competitors(
                main_insights.brand_name or URLValidator.get_domain(request.website_url),
                request.industry_keywords
            )
            
            for comp_url in competitor_urls[:request.max_competitors]:
                try:
                    async with ShopifyScraperService() as scraper:
                        comp_insights = await scraper.extract_insights(comp_url)
                        comp_insights = await data_processor.enrich_insights(comp_insights)
                        competitors.append(data_processor.generate_extraction_summary(comp_insights))
                        
                        background_tasks.add_task(db_service.save_insights, comp_insights)
                except Exception:
                    continue
        
        analysis_summary = competitor_service.generate_comparison_summary(
            main_insights,
            competitors
        )
        
        background_tasks.add_task(
            db_service.save_competitor_analysis,
            str(main_insights.website_url),
            main_insights.brand_name,
            competitors,
            analysis_summary,
            request.industry_keywords
        )
        
        return CompetitorAnalysisResponse(
            main_brand=data_processor.generate_extraction_summary(main_insights),
            competitors=competitors,
            analysis_summary=analysis_summary
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))