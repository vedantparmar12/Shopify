from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, Float, Index
from sqlalchemy.sql import func
from datetime import datetime

from app.database.connection import Base


class BrandInsightsDB(Base):
    __tablename__ = "brand_insights"
    
    id = Column(Integer, primary_key=True, index=True)
    website_url = Column(String(255), unique=True, index=True, nullable=False)
    brand_name = Column(String(255), index=True)
    
    # Product Information (stored as JSON)
    product_catalog = Column(JSON)
    hero_products = Column(JSON)
    total_products = Column(Integer, default=0)
    
    # Policies (stored as Text)
    privacy_policy = Column(Text)
    privacy_policy_url = Column(String(500))
    return_refund_policy = Column(Text)
    return_refund_policy_url = Column(String(500))
    shipping_policy = Column(Text)
    terms_of_service = Column(Text)
    
    # Brand Information
    brand_context = Column(Text)
    brand_description = Column(Text)
    faqs = Column(JSON)
    
    # Contact & Social (stored as JSON)
    social_handles = Column(JSON)
    contact_info = Column(JSON)
    important_links = Column(JSON)
    
    # Store Information
    currency = Column(String(10))
    country = Column(String(10))
    language = Column(String(10))
    is_shopify_store = Column(Boolean, default=True)
    
    # Metadata
    extraction_timestamp = Column(DateTime, default=func.now(), nullable=False)
    extraction_success = Column(Boolean, default=True)
    error_messages = Column(JSON)
    extraction_duration_seconds = Column(Float)
    quality_score = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_brand_name', 'brand_name'),
        Index('idx_extraction_timestamp', 'extraction_timestamp'),
        Index('idx_quality_score', 'quality_score'),
    )


class CompetitorAnalysis(Base):
    __tablename__ = "competitor_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    main_brand_url = Column(String(255), index=True, nullable=False)
    main_brand_name = Column(String(255))
    
    # Competitor data (stored as JSON)
    competitors = Column(JSON)
    analysis_summary = Column(Text)
    
    # Metadata
    analysis_timestamp = Column(DateTime, default=func.now(), nullable=False)
    industry_keywords = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_main_brand_url', 'main_brand_url'),
        Index('idx_analysis_timestamp', 'analysis_timestamp'),
    )


class ExtractionLog(Base):
    __tablename__ = "extraction_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    website_url = Column(String(255), index=True, nullable=False)
    
    # Status
    status = Column(String(50))  # 'success', 'failed', 'partial'
    error_message = Column(Text)
    
    # Performance metrics
    duration_seconds = Column(Float)
    data_points_extracted = Column(Integer)
    quality_score = Column(Float)
    
    # Request info
    user_ip = Column(String(50))
    user_agent = Column(String(255))
    
    # Timestamp
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_website_url_log', 'website_url'),
        Index('idx_timestamp_log', 'timestamp'),
        Index('idx_status', 'status'),
    )