from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, desc, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.database.connection import async_session
from app.database.models import BrandInsightsDB, CompetitorAnalysis, ExtractionLog
from app.models.brand_insights import BrandInsights
from app.services.data_processor import DataProcessor
from app.utils.exceptions import DatabaseException


class DatabaseService:
    def __init__(self):
        self.data_processor = DataProcessor()
        self.enabled = False
        
        # Check if database is available
        try:
            # Test connection will happen on first use
            self.enabled = True
        except Exception as e:
            print(f"Database service disabled: {e}")
            self.enabled = False
    
    async def save_insights(self, insights: BrandInsights) -> int:
        if not self.enabled:
            print("Database service is disabled, skipping save")
            return 0
            
        try:
            async with async_session() as session:
                # Check if exists
                existing = await session.execute(
                    select(BrandInsightsDB).where(
                        BrandInsightsDB.website_url == str(insights.website_url)
                    )
                )
                existing_record = existing.scalar_one_or_none()
                
                # Calculate quality score
                quality_score = self.data_processor.calculate_extraction_quality_score(insights)
                
                # Helper to convert HttpUrl to string in dicts
                def convert_urls_in_dict(d):
                    if isinstance(d, dict):
                        return {k: convert_urls_in_dict(v) for k, v in d.items()}
                    elif isinstance(d, list):
                        return [convert_urls_in_dict(item) for item in d]
                    elif hasattr(d, '__class__') and 'HttpUrl' in str(d.__class__):
                        return str(d)
                    else:
                        return d
                
                # Prepare data for database
                db_data = {
                    'website_url': str(insights.website_url),
                    'brand_name': insights.brand_name,
                    'product_catalog': convert_urls_in_dict([p.dict() for p in insights.product_catalog]),
                    'hero_products': convert_urls_in_dict([p.dict() for p in insights.hero_products]),
                    'total_products': insights.total_products,
                    'privacy_policy': insights.privacy_policy,
                    'privacy_policy_url': str(insights.privacy_policy_url) if insights.privacy_policy_url else None,
                    'return_refund_policy': insights.return_refund_policy,
                    'return_refund_policy_url': str(insights.return_refund_policy_url) if insights.return_refund_policy_url else None,
                    'shipping_policy': insights.shipping_policy,
                    'terms_of_service': insights.terms_of_service,
                    'brand_context': insights.brand_context,
                    'brand_description': insights.brand_description,
                    'faqs': convert_urls_in_dict([faq.dict() for faq in insights.faqs]),
                    'social_handles': convert_urls_in_dict([s.dict() for s in insights.social_handles]),
                    'contact_info': convert_urls_in_dict(insights.contact_info.dict()),
                    'important_links': convert_urls_in_dict([l.dict() for l in insights.important_links]),
                    'currency': insights.currency,
                    'country': insights.country,
                    'language': insights.language,
                    'is_shopify_store': insights.is_shopify_store,
                    'extraction_timestamp': insights.extraction_timestamp,
                    'extraction_success': insights.extraction_success,
                    'error_messages': insights.error_messages,
                    'extraction_duration_seconds': insights.extraction_duration_seconds,
                    'quality_score': quality_score
                }
                
                if existing_record:
                    # Update existing record
                    for key, value in db_data.items():
                        setattr(existing_record, key, value)
                    db_record = existing_record
                else:
                    # Create new record
                    db_record = BrandInsightsDB(**db_data)
                    session.add(db_record)
                
                await session.commit()
                
                # Log extraction
                await self._log_extraction(
                    session,
                    str(insights.website_url),
                    'success' if insights.extraction_success else 'failed',
                    insights.error_messages[0] if insights.error_messages else None,
                    insights.extraction_duration_seconds,
                    quality_score
                )
                
                return db_record.id
        
        except Exception as e:
            raise DatabaseException(f"Failed to save insights: {str(e)}")
    
    async def get_insights_by_url(self, website_url: str) -> Optional[BrandInsights]:
        if not self.enabled:
            return None
            
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(BrandInsightsDB).where(
                        BrandInsightsDB.website_url == website_url
                    )
                )
                db_record = result.scalar_one_or_none()
                
                if db_record:
                    return self._db_to_pydantic(db_record)
                
                return None
        
        except Exception as e:
            raise DatabaseException(f"Failed to retrieve insights: {str(e)}")
    
    async def get_recent_insights(self, limit: int = 10) -> List[BrandInsights]:
        if not self.enabled:
            return []
            
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(BrandInsightsDB)
                    .order_by(desc(BrandInsightsDB.extraction_timestamp))
                    .limit(limit)
                )
                db_records = result.scalars().all()
                
                return [self._db_to_pydantic(record) for record in db_records]
        
        except Exception as e:
            raise DatabaseException(f"Failed to retrieve recent insights: {str(e)}")
    
    async def search_insights(
        self,
        brand_name: Optional[str] = None,
        country: Optional[str] = None,
        min_quality_score: Optional[float] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 20
    ) -> List[BrandInsights]:
        try:
            async with async_session() as session:
                query = select(BrandInsightsDB)
                
                # Apply filters
                conditions = []
                if brand_name:
                    conditions.append(BrandInsightsDB.brand_name.ilike(f"%{brand_name}%"))
                if country:
                    conditions.append(BrandInsightsDB.country == country)
                if min_quality_score:
                    conditions.append(BrandInsightsDB.quality_score >= min_quality_score)
                if start_date:
                    conditions.append(BrandInsightsDB.extraction_timestamp >= start_date)
                if end_date:
                    conditions.append(BrandInsightsDB.extraction_timestamp <= end_date)
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                query = query.order_by(desc(BrandInsightsDB.extraction_timestamp)).limit(limit)
                
                result = await session.execute(query)
                db_records = result.scalars().all()
                
                return [self._db_to_pydantic(record) for record in db_records]
        
        except Exception as e:
            raise DatabaseException(f"Failed to search insights: {str(e)}")
    
    async def get_extraction_statistics(self) -> Dict[str, Any]:
        try:
            async with async_session() as session:
                # Total extractions
                total_result = await session.execute(
                    select(func.count(BrandInsightsDB.id))
                )
                total_extractions = total_result.scalar()
                
                # Successful extractions
                success_result = await session.execute(
                    select(func.count(BrandInsightsDB.id)).where(
                        BrandInsightsDB.extraction_success == True
                    )
                )
                successful_extractions = success_result.scalar()
                
                # Average quality score
                avg_quality_result = await session.execute(
                    select(func.avg(BrandInsightsDB.quality_score))
                )
                avg_quality_score = avg_quality_result.scalar()
                
                # Average extraction time
                avg_time_result = await session.execute(
                    select(func.avg(BrandInsightsDB.extraction_duration_seconds))
                )
                avg_extraction_time = avg_time_result.scalar()
                
                # Extractions in last 24 hours
                yesterday = datetime.utcnow() - timedelta(days=1)
                recent_result = await session.execute(
                    select(func.count(BrandInsightsDB.id)).where(
                        BrandInsightsDB.extraction_timestamp >= yesterday
                    )
                )
                recent_extractions = recent_result.scalar()
                
                # Top countries
                country_result = await session.execute(
                    select(
                        BrandInsightsDB.country,
                        func.count(BrandInsightsDB.id).label('count')
                    )
                    .group_by(BrandInsightsDB.country)
                    .order_by(desc('count'))
                    .limit(5)
                )
                top_countries = [
                    {'country': row[0], 'count': row[1]}
                    for row in country_result.all()
                ]
                
                return {
                    'total_extractions': total_extractions or 0,
                    'successful_extractions': successful_extractions or 0,
                    'success_rate': (successful_extractions / total_extractions * 100) if total_extractions else 0,
                    'average_quality_score': round(avg_quality_score or 0, 2),
                    'average_extraction_time_seconds': round(avg_extraction_time or 0, 2),
                    'extractions_last_24h': recent_extractions or 0,
                    'top_countries': top_countries
                }
        
        except Exception as e:
            raise DatabaseException(f"Failed to get statistics: {str(e)}")
    
    async def save_competitor_analysis(
        self,
        main_brand_url: str,
        main_brand_name: str,
        competitors: List[Dict],
        analysis_summary: str,
        industry_keywords: Optional[List[str]] = None
    ) -> int:
        if not self.enabled:
            return 0
            
        try:
            async with async_session() as session:
                analysis = CompetitorAnalysis(
                    main_brand_url=main_brand_url,
                    main_brand_name=main_brand_name,
                    competitors=competitors,
                    analysis_summary=analysis_summary,
                    industry_keywords=industry_keywords
                )
                session.add(analysis)
                await session.commit()
                return analysis.id
        
        except Exception as e:
            raise DatabaseException(f"Failed to save competitor analysis: {str(e)}")
    
    async def _log_extraction(
        self,
        session: AsyncSession,
        website_url: str,
        status: str,
        error_message: Optional[str],
        duration_seconds: Optional[float],
        quality_score: Optional[float]
    ):
        try:
            log = ExtractionLog(
                website_url=website_url,
                status=status,
                error_message=error_message,
                duration_seconds=duration_seconds,
                quality_score=quality_score
            )
            session.add(log)
            await session.commit()
        except:
            pass  # Don't fail main operation if logging fails
    
    def _db_to_pydantic(self, db_record: BrandInsightsDB) -> BrandInsights:
        # Convert database record to Pydantic model
        data = {
            'website_url': db_record.website_url,
            'brand_name': db_record.brand_name,
            'product_catalog': db_record.product_catalog or [],
            'hero_products': db_record.hero_products or [],
            'total_products': db_record.total_products,
            'privacy_policy': db_record.privacy_policy,
            'privacy_policy_url': db_record.privacy_policy_url,
            'return_refund_policy': db_record.return_refund_policy,
            'return_refund_policy_url': db_record.return_refund_policy_url,
            'shipping_policy': db_record.shipping_policy,
            'terms_of_service': db_record.terms_of_service,
            'brand_context': db_record.brand_context,
            'brand_description': db_record.brand_description,
            'faqs': db_record.faqs or [],
            'social_handles': db_record.social_handles or [],
            'contact_info': db_record.contact_info or {},
            'important_links': db_record.important_links or [],
            'currency': db_record.currency,
            'country': db_record.country,
            'language': db_record.language,
            'is_shopify_store': db_record.is_shopify_store,
            'extraction_timestamp': db_record.extraction_timestamp,
            'extraction_success': db_record.extraction_success,
            'error_messages': db_record.error_messages or [],
            'extraction_duration_seconds': db_record.extraction_duration_seconds
        }
        
        return BrandInsights(**data)