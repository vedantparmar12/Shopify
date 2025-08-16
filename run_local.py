#!/usr/bin/env python3
"""
Local runner script to test the Shopify Insights Fetcher API
"""

import asyncio
import json
import sys
import os

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_server():
    """Run the FastAPI server with uvicorn"""
    import uvicorn
    
    print("\n" + "="*60)
    print("SHOPIFY INSIGHTS FETCHER - LOCAL TEST SERVER")
    print("="*60)
    print("\nStarting server...")
    print("API Documentation will be available at:")
    print("  - Swagger UI: http://localhost:8000/docs")
    print("  - ReDoc: http://localhost:8000/redoc")
    print("\nTest endpoints:")
    print("  - GET  http://localhost:8000/")
    print("  - POST http://localhost:8000/api/version1/extract")
    print("  - POST http://localhost:8000/api/version1/competitors")
    print("\n" + "="*60 + "\n")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    run_server()