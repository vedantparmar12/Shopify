#!/usr/bin/env python3
"""Quick test to verify the API is working correctly"""

import requests
import json

def test_api():
    """Quick test of the extraction endpoint"""
    
    print("\n" + "="*60)
    print("QUICK API TEST - Shopify Insights Fetcher")
    print("="*60)
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        print(f"\nServer Status: {'Running' if response.status_code == 200 else 'Error'}")
    except:
        print("\nError: Server is not running!")
        print("Please start the server first with:")
        print("  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        return
    
    # Test extraction
    print("\nTesting extraction endpoint...")
    print("-" * 40)
    
    test_url = "https://memy.co.in"
    print(f"Test URL: {test_url}")
    
    response = requests.post(
        "http://localhost:8000/api/version1/extract",
        json={"website_url": test_url},
        timeout=60
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        print("\nExtraction Results:")
        print(f"  Brand Name: {data.get('brand_name', 'Not found')}")
        print(f"  Products Found: {data.get('total_products', 0)}")
        print(f"  Hero Products: {len(data.get('hero_products', []))}")
        print(f"  FAQs: {len(data.get('faqs', []))}")
        print(f"  Social Handles: {len(data.get('social_handles', []))}")
        print(f"  Has Privacy Policy: {'Yes' if data.get('privacy_policy') else 'No'}")
        print(f"  Has Return Policy: {'Yes' if data.get('return_refund_policy') else 'No'}")
        print(f"  Has Contact Info: {'Yes' if data.get('contact_info') else 'No'}")
        print(f"  Important Links: {len(data.get('important_links', []))}")
        print(f"  Extraction Success: {data.get('extraction_success', False)}")
        
        # Check all mandatory requirements
        print("\nMandatory Requirements:")
        checks = {
            "1. Product Catalog": len(data.get('product_catalog', [])) > 0,
            "2. Hero Products": len(data.get('hero_products', [])) > 0,
            "3. Privacy Policy": bool(data.get('privacy_policy')),
            "4. Return Policy": bool(data.get('return_refund_policy')),
            "5. FAQs": len(data.get('faqs', [])) > 0,
            "6. Social Handles": len(data.get('social_handles', [])) > 0,
            "7. Contact Info": bool(data.get('contact_info')),
            "8. Brand Context": bool(data.get('brand_context')),
            "9. Important Links": len(data.get('important_links', [])) > 0
        }
        
        all_passed = True
        for req, passed in checks.items():
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {req}")
            if not passed:
                all_passed = False
        
        print("\n" + "="*60)
        if all_passed:
            print("SUCCESS: All requirements met!")
        else:
            print("PARTIAL: Some requirements not met")
        print("="*60)
        
    else:
        print(f"\nError: {response.status_code}")
        print(f"Response: {response.text[:200]}")

if __name__ == "__main__":
    test_api()