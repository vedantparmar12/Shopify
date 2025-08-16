#!/usr/bin/env python3
"""Verify API is working correctly with all requirements"""

import requests
import json

def verify():
    print("\n" + "="*60)
    print("VERIFYING SHOPIFY INSIGHTS API")
    print("="*60)
    
    # Test extraction
    url = "http://localhost:8000/api/version1/extract"
    data = {"website_url": "https://memy.co.in"}
    
    print("\nTesting: https://memy.co.in")
    response = requests.post(url, json=data, timeout=60)
    
    if response.status_code == 200:
        result = response.json()
        
        print("\n✅ SUCCESS - API Response Received")
        print("-" * 40)
        
        # Check all 9 requirements
        checks = [
            ("1. Product Catalog", len(result.get('product_catalog', [])), "products"),
            ("2. Hero Products", len(result.get('hero_products', [])), "products"),
            ("3. Privacy Policy", len(str(result.get('privacy_policy', ''))) if result.get('privacy_policy') else 0, "chars"),
            ("4. Return Policy", len(str(result.get('return_refund_policy', ''))) if result.get('return_refund_policy') else 0, "chars"),
            ("5. FAQs", len(result.get('faqs', [])), "items"),
            ("6. Social Handles", len(result.get('social_handles', [])), "handles"),
            ("7. Contact Info", len(result.get('contact_info', {}).get('emails', [])) + len(result.get('contact_info', {}).get('phone_numbers', [])), "items"),
            ("8. Brand Context", len(str(result.get('brand_context', ''))) if result.get('brand_context') else 0, "chars"),
            ("9. Important Links", len(result.get('important_links', [])), "links")
        ]
        
        print("\nMANDATORY REQUIREMENTS:")
        for name, count, unit in checks:
            status = "✓" if count > 0 else "✗"
            print(f"[{status}] {name}: {count} {unit}")
        
        # Show extracted data
        print("\nEXTRACTED DATA:")
        print(f"Brand: {result.get('brand_name', 'Not found')}")
        print(f"Total Products: {result.get('total_products', 0)}")
        print(f"Extraction Success: {result.get('extraction_success', False)}")
        
        # Count passed requirements
        passed = sum(1 for _, count, _ in checks if count > 0)
        print(f"\nRESULT: {passed}/9 requirements met")
        
        if passed == 9:
            print("✅ ALL REQUIREMENTS MET - API IS WORKING PERFECTLY!")
        elif passed >= 7:
            print("✓ MOST REQUIREMENTS MET - API IS WORKING WELL!")
        else:
            print("⚠ SOME REQUIREMENTS MISSING - CHECK IMPLEMENTATION")
            
    else:
        print(f"\n❌ ERROR: Status {response.status_code}")
        print(f"Response: {response.text[:500]}")

if __name__ == "__main__":
    verify()