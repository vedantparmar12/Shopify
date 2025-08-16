from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ErrorResponse(BaseModel):
    error: str
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[Dict[str, Any]] = None


class SuccessResponse(BaseModel):
    message: str
    status_code: int = 200
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CompetitorAnalysisRequest(BaseModel):
    website_url: str
    find_competitors: bool = True
    max_competitors: int = 5
    industry_keywords: Optional[List[str]] = None


class CompetitorAnalysisResponse(BaseModel):
    main_brand: Dict[str, Any]
    competitors: List[Dict[str, Any]]
    analysis_summary: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BulkExtractionRequest(BaseModel):
    website_urls: List[str]
    concurrent_limit: int = Field(default=3, le=10)
    include_competitors: bool = False


class BulkExtractionResponse(BaseModel):
    successful_extractions: List[Dict[str, Any]]
    failed_extractions: List[Dict[str, str]]
    total_processed: int
    success_rate: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)