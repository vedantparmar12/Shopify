#!/usr/bin/env python3
"""
Test script to verify Scrapy implementation meets all assignment requirements
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_STORES = [
    "https://memy.co.in",
    "https://hairoriginals.com", 
    "https://colourpop.com"
]

def print_section(title: str):
    """Print formatted section header"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def check_mandatory_fields(data: Dict[str, Any]) -> Dict[str, bool]:
    """Check if all 9 mandatory fields are present and populated"""
    
    checks = {
        "1. Product Catalog": bool(data.get("product_catalog")) and len(data.get("product_catalog", [])) > 0,
        "2. Hero Products": bool(data.get("hero_products")) and len(data.get("hero_products", [])) > 0,
        "3. Privacy Policy": bool(data.get("privacy_policy")) and len(str(data.get("privacy_policy", ""))) > 100,
        "4. Return/Refund Policy": bool(data.get("return_refund_policy")) and len(str(data.get("return_refund_policy", ""))) > 100,
        "5. Brand FAQs": bool(data.get("faqs")) and len(data.get("faqs", [])) > 0,
        "6. Social Handles": bool(data.get("social_handles")) and len(data.get("social_handles", [])) > 0,
        "7. Contact Info": bool(data.get("contact_info")) and (
            bool(data.get("contact_info", {}).get("emails")) or 
            bool(data.get("contact_info", {}).get("phone_numbers"))
        ),
        "8. Brand Context": bool(data.get("brand_context")) and len(str(data.get("brand_context", ""))) > 50,
        "9. Important Links": bool(data.get("important_links")) and len(data.get("important_links", [])) > 0
    }
    
    return checks

def test_extraction_endpoint(store_url: str):
    """Test the /api/version1/extract endpoint"""
    
    print(f"\nTesting: {store_url}")
    print("-" * 40)
    
    # Prepare request
    endpoint = f"{API_BASE_URL}/api/version1/extract"
    payload = {"website_url": store_url}
    
    try:
        # Make request
        start_time = time.time()
        response = requests.post(endpoint, json=payload, timeout=60)
        elapsed_time = time.time() - start_time
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Time: {elapsed_time:.2f} seconds")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check mandatory fields
            print("\nMandatory Requirements Check:")
            checks = check_mandatory_fields(data)
            
            all_passed = True
            for requirement, passed in checks.items():
                status = "PASS" if passed else "FAIL"
                symbol = "[✓]" if passed else "[✗]"
                print(f"  {symbol} {requirement}: {status}")
                if not passed:
                    all_passed = False
            
            # Display summary
            print(f"\nExtraction Summary:")
            print(f"  Brand Name: {data.get('brand_name', 'Not found')}")
            print(f"  Website URL: {data.get('website_url')}")
            print(f"  Total Products: {data.get('total_products', len(data.get('product_catalog', [])))}")
            print(f"  Hero Products: {len(data.get('hero_products', []))}")
            print(f"  FAQs Count: {len(data.get('faqs', []))}")
            print(f"  Social Platforms: {len(data.get('social_handles', []))}")
            
            # Show sample data
            if data.get('product_catalog'):
                print(f"\nSample Product:")
                product = data['product_catalog'][0]
                print(f"  - Name: {product.get('name', 'N/A')}")
                print(f"  - Price: {product.get('price', 'N/A')}")
                print(f"  - URL: {product.get('product_url', 'N/A')}")
            
            if data.get('faqs'):
                print(f"\nSample FAQ:")
                faq = data['faqs'][0]
                print(f"  Q: {faq.get('question', 'N/A')[:100]}")
                print(f"  A: {faq.get('answer', 'N/A')[:100]}...")
            
            if data.get('social_handles'):
                print(f"\nSocial Media:")
                for social in data['social_handles'][:3]:
                    print(f"  - {social.get('platform', 'N/A')}: {social.get('handle', social.get('url', 'N/A'))}")
            
            # Overall result
            if all_passed:
                print(f"\nResult: SUCCESS - All mandatory requirements met!")
            else:
                print(f"\nResult: PARTIAL - Some requirements not met")
            
            return all_passed, data
            
        elif response.status_code == 404:
            print("Error: Website not found (404)")
            return False, None
        elif response.status_code == 500:
            print(f"Error: Internal server error (500)")
            print(f"Details: {response.json().get('error', 'Unknown error')}")
            return False, None
        else:
            print(f"Unexpected status code: {response.status_code}")
            return False, None
            
    except requests.exceptions.Timeout:
        print("Error: Request timed out")
        return False, None
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API. Is the server running?")
        print("Start the server with: python run_local.py")
        return False, None
    except Exception as e:
        print(f"Error: {e}")
        return False, None

def test_competitor_endpoint(store_url: str):
    """Test the /api/version1/competitors endpoint (bonus feature)"""
    
    print_section("BONUS: Competitor Analysis Test")
    
    endpoint = f"{API_BASE_URL}/api/version1/competitors"
    payload = {
        "website_url": store_url,
        "find_competitors": True,
        "max_competitors": 5
    }
    
    try:
        response = requests.post(endpoint, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"Competitors Found: {data.get('competitors_found', 0)}")
            
            if data.get('competitor_urls'):
                print("\nCompetitor URLs:")
                for url in data['competitor_urls'][:5]:
                    print(f"  - {url}")
            
            if data.get('competitor_insights'):
                print("\nCompetitor Insights:")
                for comp in data['competitor_insights'][:3]:
                    print(f"  - {comp.get('brand_name', 'Unknown')}: {comp.get('total_products', 0)} products")
            
            return True
        else:
            print(f"Competitor analysis failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Competitor analysis error: {e}")
        return False

def main():
    """Run all tests"""
    
    print_section("SHOPIFY INSIGHTS FETCHER - API TEST")
    print("\nThis test verifies that the Scrapy implementation meets")
    print("all assignment requirements for the GenAI Developer Intern position.")
    
    # Check if server is running
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        if response.status_code != 200:
            print("\nError: API server is not responding correctly")
            print("Please start the server with: python run_local.py")
            return
    except:
        print("\nError: Cannot connect to API server at", API_BASE_URL)
        print("Please start the server first with: python run_local.py")
        return
    
    print("\nServer is running. Starting tests...")
    
    # Test extraction for each store
    results = []
    for store_url in TEST_STORES:
        print_section(f"Testing Store: {store_url}")
        success, data = test_extraction_endpoint(store_url)
        results.append({
            "store": store_url,
            "success": success,
            "brand": data.get("brand_name") if data else None,
            "products": data.get("total_products", 0) if data else 0
        })
        
        # Small delay between requests
        time.sleep(2)
    
    # Test competitor analysis (bonus)
    test_competitor_endpoint(TEST_STORES[0])
    
    # Final summary
    print_section("TEST SUMMARY")
    
    print("\nCore Requirements Test Results:")
    for result in results:
        status = "PASS" if result["success"] else "FAIL"
        print(f"  [{status}] {result['store']}")
        if result["success"]:
            print(f"       Brand: {result['brand']}, Products: {result['products']}")
    
    # Check overall success
    all_passed = all(r["success"] for r in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("FINAL RESULT: ALL TESTS PASSED")
        print("The implementation meets all mandatory requirements!")
    else:
        print("FINAL RESULT: SOME TESTS FAILED")
        print("Please check the implementation and try again.")
    print("="*60)

if __name__ == "__main__":
    main()