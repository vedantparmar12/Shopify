from pydantic import BaseModel, HttpUrl, EmailStr, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime


class ProductInfo(BaseModel):
    name: str
    price: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    product_url: Optional[HttpUrl] = None
    description: Optional[str] = None
    sku: Optional[str] = None
    vendor: Optional[str] = None
    product_type: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    available: Optional[bool] = True


class SocialHandle(BaseModel):
    platform: str
    url: HttpUrl
    handle: Optional[str] = None
    
    @field_validator('platform')
    @classmethod
    def validate_platform(cls, v):
        valid_platforms = ['facebook', 'instagram', 'twitter', 'tiktok', 'youtube', 'pinterest', 'linkedin', 'snapchat']
        if v.lower() not in valid_platforms:
            return 'other'
        return v.lower()


class FAQ(BaseModel):
    question: str
    answer: str
    category: Optional[str] = None


class ContactInfo(BaseModel):
    emails: List[EmailStr] = Field(default_factory=list)
    phone_numbers: List[str] = Field(default_factory=list)
    address: Optional[str] = None
    support_hours: Optional[str] = None


class ImportantLink(BaseModel):
    name: str
    url: HttpUrl
    category: str
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v):
        valid_categories = ['support', 'tracking', 'blog', 'about', 'legal', 'help', 'account']
        if v.lower() not in valid_categories:
            return 'other'
        return v.lower()


class BrandInsights(BaseModel):
    website_url: HttpUrl
    brand_name: Optional[str] = None
    
    # Product Information
    product_catalog: List[ProductInfo] = Field(default_factory=list)
    hero_products: List[ProductInfo] = Field(default_factory=list)
    total_products: Optional[int] = 0
    
    # Policies
    privacy_policy: Optional[str] = None
    privacy_policy_url: Optional[HttpUrl] = None
    return_refund_policy: Optional[str] = None
    return_refund_policy_url: Optional[HttpUrl] = None
    shipping_policy: Optional[str] = None
    terms_of_service: Optional[str] = None
    
    # Brand Information
    brand_context: Optional[str] = None
    brand_description: Optional[str] = None
    faqs: List[FAQ] = Field(default_factory=list)
    
    # Contact & Social
    social_handles: List[SocialHandle] = Field(default_factory=list)
    contact_info: ContactInfo = Field(default_factory=ContactInfo)
    important_links: List[ImportantLink] = Field(default_factory=list)
    
    # Store Information
    currency: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None
    is_shopify_store: bool = True
    
    # Metadata
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)
    extraction_success: bool = True
    error_messages: List[str] = Field(default_factory=list)
    extraction_duration_seconds: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: lambda v: str(v)
        }