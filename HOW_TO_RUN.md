# How to Run and Test the Shopify Insights Fetcher

## Prerequisites
- Python 3.11 or higher
- pip (Python package manager)
- Optional: MySQL server (for bonus database features)

## Quick Start

### Option 1: Using Startup Scripts

**For Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

**For Windows:**
```cmd
start.bat
```

### Option 2: Manual Setup with uvicorn

1. **Create virtual environment:**
```bash
python -m venv .venv

# Linux/Mac:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run with uvicorn:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The server will start at: **http://localhost:8000**

## Verify Scrapy is Working

### Step 1: Start the Server
Run one of the commands above. You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
Starting Shopify Insights API...
```

### Step 2: Check API Documentation
Open your browser and visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Step 3: Test with the Automated Test Script

In a new terminal window (keep server running):
```bash
python test_scrapy_api.py
```

This will test all 9 mandatory requirements:
1. Product Catalog
2. Hero Products  
3. Privacy Policy
4. Return/Refund Policy
5. Brand FAQs
6. Social Handles
7. Contact Info
8. Brand Context
9. Important Links

### Step 4: Manual Testing with curl

**Test Extraction (Main Requirement):**
```bash
curl -X POST http://localhost:8000/api/version1/extract \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://memy.co.in"}'
```

**Test Competitor Analysis (Bonus):**
```bash
curl -X POST http://localhost:8000/api/version1/competitors \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://colourpop.com", "find_competitors": true, "max_competitors": 5}'
```

## Expected Output

When testing with `https://memy.co.in`, you should see:

```json
{
  "website_url": "https://memy.co.in",
  "brand_name": "Memy",
  "product_catalog": [
    {
      "name": "Product Name",
      "price": "₹999",
      "product_url": "https://memy.co.in/products/...",
      ...
    }
  ],
  "hero_products": [...],
  "privacy_policy": "Privacy policy content...",
  "return_refund_policy": "Return policy content...",
  "faqs": [
    {
      "question": "Do you have COD?",
      "answer": "Yes, we do..."
    }
  ],
  "social_handles": [
    {
      "platform": "instagram",
      "handle": "@memy",
      "url": "https://instagram.com/memy"
    }
  ],
  "contact_info": {
    "emails": ["support@memy.co.in"],
    "phone_numbers": ["+91-xxxxx"]
  },
  "important_links": [...],
  "brand_context": "About the brand...",
  "extraction_success": true
}
```

## Testing Different Stores

Test with these verified Shopify stores:
- `https://memy.co.in` - Indian fashion brand
- `https://hairoriginals.com` - Hair products
- `https://colourpop.com` - Cosmetics (large catalog)
- `https://jeffreestarcosmetics.com` - Beauty products
- `https://gymshark.com` - Fitness apparel

## Verify Scrapy Implementation

The app uses Scrapy spider (`app/services/scrapy_scraper_service.py`) which:

1. **Detects Shopify stores** - Checks for Shopify markers
2. **Fetches products** - Uses `/products.json` endpoint
3. **Extracts policies** - Scrapes policy pages
4. **Finds FAQs** - Parses FAQ sections
5. **Gets social links** - Extracts from footer/header
6. **Collects contact info** - Uses regex patterns
7. **Concurrent requests** - Scrapy handles multiple pages

You can see Scrapy working in the console output:
```
Starting Scrapy extraction from: https://memy.co.in
Found 25 products in products.json
Extracted policies
Found 5 FAQs
Found 3 social handles
Scrapy extraction completed in 8.45 seconds
```

## Troubleshooting

### Server won't start
- Check Python version: `python --version` (should be 3.11+)
- Install dependencies: `pip install -r requirements.txt`

### Extraction fails
- Verify the URL is a Shopify store
- Check internet connection
- Some stores may have rate limiting

### No products found
- The store might have disabled `/products.json`
- Try a different test store

### Database features (bonus)
To enable MySQL persistence:
1. Install MySQL server
2. Update `.env` with your database credentials
3. The app will automatically use the database if available

## Success Criteria

The implementation is successful when:
- All 9 mandatory data points are extracted
- API returns proper status codes (200, 404, 500)
- Extraction completes within 30 seconds
- Competitor analysis works (bonus)
- Data can be persisted to MySQL (bonus)

## Performance Metrics

Typical extraction times:
- Small store (< 50 products): 5-10 seconds
- Medium store (50-500 products): 10-20 seconds  
- Large store (> 500 products): 20-30 seconds

## Support

If you encounter issues:
1. Check the console output for error messages
2. Verify the store URL is correct
3. Ensure all dependencies are installed
4. Try with a different Shopify store