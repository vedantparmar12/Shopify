#!/usr/bin/env python3
"""Test script to verify the Shopify Insights Fetcher implementation."""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any

# Test stores
TEST_STORES = [
    "https://memy.co.in",
    "https://colourpop.com",
    "https://jeffreestarcosmetics.com"
]


async def test_extraction():
    """Test the extraction functionality."""
    from app.services.scrapy_scraper_service import ScrapyShopifyScraperService
    from app.database.service import DatabaseService
    
    print("=" * 60)
    print("SHOPIFY INSIGHTS FETCHER - TEST SUITE")
    print("=" * 60)
    
    results = []
    
    for store_url in TEST_STORES[:1]:  # Test with first store
        print(f"\n📍 Testing: {store_url}")
        print("-" * 40)
        
        try:
            # Test extraction
            async with ScrapyShopifyScraperService() as scraper:
                insights = await scraper.extract_insights(store_url)
            
            # Verify mandatory data points
            mandatory_checks = {
                "1. Brand Name": bool(insights.brand_name),
                "2. Product Catalog": len(insights.product_catalog) > 0,
                "3. Hero Products": len(insights.hero_products) > 0,
                "4. Privacy Policy": bool(insights.privacy_policy),
                "5. Return/Refund Policy": bool(insights.return_refund_policy),
                "6. FAQs": len(insights.faqs) > 0,
                "7. Social Handles": len(insights.social_handles) > 0,
                "8. Contact Info": bool(insights.contact_info.emails or insights.contact_info.phone_numbers),
                "9. Brand Context": bool(insights.brand_context),
                "10. Important Links": len(insights.important_links) > 0
            }
            
            print("\n✅ Mandatory Data Points Check:")
            all_passed = True
            for check, passed in mandatory_checks.items():
                status = "✓" if passed else "✗"
                print(f"  {status} {check}: {'PASS' if passed else 'FAIL'}")
                if not passed:
                    all_passed = False
            
            # Show extracted data summary
            print(f"\n📊 Extraction Summary:")
            print(f"  - Brand: {insights.brand_name}")
            print(f"  - Products: {len(insights.product_catalog)}")
            print(f"  - Hero Products: {len(insights.hero_products)}")
            print(f"  - FAQs: {len(insights.faqs)}")
            print(f"  - Social Platforms: {[s.platform for s in insights.social_handles]}")
            print(f"  - Emails: {insights.contact_info.emails[:2] if insights.contact_info.emails else 'None'}")
            print(f"  - Is Shopify: {insights.is_shopify_store}")
            print(f"  - Extraction Time: {insights.extraction_duration_seconds:.2f}s")
            
            # Test database persistence (bonus)
            try:
                db_service = DatabaseService()
                if db_service.enabled:
                    db_id = await db_service.save_insights(insights)
                    print(f"\n💾 Database: Saved with ID {db_id}")
                else:
                    print(f"\n⚠️ Database: Service disabled")
            except Exception as e:
                print(f"\n⚠️ Database: {e}")
            
            results.append({
                "store": store_url,
                "success": all_passed,
                "brand": insights.brand_name,
                "products": len(insights.product_catalog)
            })
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            results.append({
                "store": store_url,
                "success": False,
                "error": str(e)
            })
    
    return results


async def test_competitor_analysis():
    """Test the competitor analysis functionality (bonus)."""
    from app.services.competitor_service import CompetitorAnalysisService
    
    print("\n" + "=" * 60)
    print("COMPETITOR ANALYSIS TEST (BONUS FEATURE)")
    print("=" * 60)
    
    test_brand = "colourpop"
    test_url = "https://colourpop.com"
    
    try:
        async with CompetitorAnalysisService() as comp_service:
            print(f"\n🔍 Finding competitors for: {test_brand}")
            
            competitors = await comp_service.find_competitors(
                brand_name=test_brand,
                industry_keywords=["cosmetics", "makeup", "beauty"],
                max_results=5
            )
            
            print(f"\n📋 Competitors Found: {len(competitors)}")
            for i, comp_url in enumerate(competitors, 1):
                print(f"  {i}. {comp_url}")
            
            return {"success": True, "competitors": len(competitors)}
            
    except Exception as e:
        print(f"\n❌ Competitor Analysis Error: {e}")
        return {"success": False, "error": str(e)}


async def test_api_endpoints():
    """Test the FastAPI endpoints."""
    print("\n" + "=" * 60)
    print("API ENDPOINTS TEST")
    print("=" * 60)
    
    import httpx
    from contextlib import asynccontextmanager
    
    # Start the FastAPI app in test mode
    from app.main import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    # Test extraction endpoint
    print("\n📡 Testing /api/version1/extract endpoint...")
    response = client.post(
        "/api/version1/extract",
        json={"website_url": "https://memy.co.in"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"  ✅ Status: {response.status_code}")
        print(f"  ✅ Brand: {data.get('brand_name')}")
        print(f"  ✅ Products: {data.get('total_products')}")
    else:
        print(f"  ❌ Status: {response.status_code}")
        print(f"  ❌ Error: {response.text[:200]}")
    
    # Test competitor endpoint
    print("\n📡 Testing /api/version1/competitors endpoint...")
    response = client.post(
        "/api/version1/competitors",
        json={
            "website_url": "https://colourpop.com",
            "find_competitors": True,
            "max_competitors": 3
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"  ✅ Status: {response.status_code}")
        print(f"  ✅ Competitors Found: {data.get('competitors_found')}")
    else:
        print(f"  ❌ Status: {response.status_code}")
    
    return {"extraction": response.status_code == 200}


async def main():
    """Run all tests."""
    print("\n🚀 Starting Shopify Insights Fetcher Tests...\n")
    
    # Test 1: Core extraction
    extraction_results = await test_extraction()
    
    # Test 2: Competitor analysis (bonus)
    competitor_results = await test_competitor_analysis()
    
    # Test 3: API endpoints
    api_results = await test_api_endpoints()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    print("\n✅ Core Features:")
    for result in extraction_results:
        status = "✓" if result.get("success") else "✗"
        print(f"  {status} {result['store']}: {result.get('brand', 'Failed')}")
    
    print("\n✅ Bonus Features:")
    print(f"  {'✓' if competitor_results['success'] else '✗'} Competitor Analysis")
    print(f"  {'✓' if api_results.get('extraction') else '✗'} API Endpoints")
    
    print("\n" + "=" * 60)
    print("✨ Testing Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())