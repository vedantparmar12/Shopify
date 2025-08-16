#!/usr/bin/env python3
"""Simple test to verify API is working"""

import requests
import json

def test():
    url = "http://localhost:8000/api/version1/extract"
    data = {"website_url": "https://memy.co.in"}
    
    print("Testing extraction endpoint...")
    response = requests.post(url, json=data, timeout=60)
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\nSuccess! Data extracted:")
        print(f"- Brand: {result.get('brand_name')}")
        print(f"- Products: {result.get('total_products')}")
        print(f"- FAQs: {len(result.get('faqs', []))}")
        print(f"- Social: {len(result.get('social_handles', []))}")
        
        # Check all 9 requirements
        checks = [
            ("Product Catalog", len(result.get('product_catalog', [])) > 0),
            ("Hero Products", len(result.get('hero_products', [])) > 0),
            ("Privacy Policy", bool(result.get('privacy_policy'))),
            ("Return Policy", bool(result.get('return_refund_policy'))),
            ("FAQs", len(result.get('faqs', [])) > 0),
            ("Social Handles", len(result.get('social_handles', [])) > 0),
            ("Contact Info", bool(result.get('contact_info'))),
            ("Brand Context", bool(result.get('brand_context'))),
            ("Important Links", len(result.get('important_links', [])) > 0)
        ]
        
        print("\nRequirements Check:")
        for name, passed in checks:
            print(f"[{'PASS' if passed else 'FAIL'}] {name}")
    else:
        print(f"Error: {response.text[:200]}")

if __name__ == "__main__":
    test()