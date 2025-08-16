from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from app.routes import core_insights
from app.utils.exceptions import InsightsAPIException

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Shopify Insights API...")
    yield
    print("Shutting down application...")


app = FastAPI(
    title="Shopify Store Insights Fetcher",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(InsightsAPIException)
async def insights_exception_handler(request: Request, exc: InsightsAPIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "status_code": exc.status_code,
            "details": exc.details
        }
    )

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint not found",
            "status_code": 404,
            "path": str(request.url)
        }
    )

# Include only the core insights router
app.include_router(core_insights.router)

@app.get("/")
async def root():
    return {
        "message": "Shopify Store Insights Fetcher API",
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "extract_insights": {
                "method": "POST",
                "path": "/api/version1/extract",
                "description": "Extract comprehensive brand insights from a Shopify store",
                "body": {
                    "website_url": "https://example-store.com"
                }
            },
            "analyze_competitors": {
                "method": "POST", 
                "path": "/api/version1/competitors",
                "description": "Find and analyze competitors for a Shopify store",
                "body": {
                    "website_url": "https://example-store.com",
                    "find_competitors": True,
                    "max_competitors": 5
                }
            }
        },
        "test_example": {
            "extract": "curl -X POST http://localhost:8000/api/version1/extract -H 'Content-Type: application/json' -d '{\"website_url\": \"https://jeffreestarcosmetics.com\"}'",
            "competitors": "curl -X POST http://localhost:8000/api/version1/competitors -H 'Content-Type: application/json' -d '{\"website_url\": \"https://colourpop.com\", \"max_competitors\": 5}'"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "Shopify Insights API",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )