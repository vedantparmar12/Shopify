# Complete Guide: Run and Test Shopify Insights Fetcher

## Step 1: Install Dependencies

```bash
# Create virtual environment (optional but recommended)
python -m venv .venv

# Activate virtual environment
# Linux/Mac:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install all required packages
pip install -r requirements.txt
```

## Step 2: Start the Server

### Option A: Direct uvicorn command (RECOMMENDED)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Option B: Using Python script
```bash
python run_local.py
```

### Option C: Using startup scripts
```bash
# Linux/Mac
./start.sh

# Windows
start.bat
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
Starting Shopify Insights API...
```

## Step 3: Verify API is Running

Open your browser and visit:
- **API Home**: http://localhost:8000/
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Step 4: Test the Implementation

### Quick Test (Recommended)
In a new terminal (keep server running):
```bash
python quick_test.py
```

This will test extraction from memy.co.in and verify all 9 mandatory requirements.

### Full Test Suite
```bash
python test_scrapy_api.py
```

This tests multiple stores and competitor analysis.

### Manual Test with curl
```bash
# Test extraction
curl -X POST http://localhost:8000/api/version1/extract \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://memy.co.in"}'

# Test competitor analysis (bonus)
curl -X POST http://localhost:8000/api/version1/competitors \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://colourpop.com", "find_competitors": true}'
```

### Test via Swagger UI
1. Go to http://localhost:8000/docs
2. Click on `POST /api/version1/extract`
3. Click "Try it out"
4. Enter: `{"website_url": "https://memy.co.in"}`
5. Click "Execute"

## Expected Output

When testing with memy.co.in, you should see all 9 mandatory data points:

```
Extraction Results:
  Brand Name: Memy
  Products Found: 25+
  Hero Products: 5
  FAQs: 3+
  Social Handles: 2+
  Has Privacy Policy: Yes
  Has Return Policy: Yes
  Has Contact Info: Yes
  Important Links: 5+
  Extraction Success: True

Mandatory Requirements:
  [PASS] 1. Product Catalog
  [PASS] 2. Hero Products
  [PASS] 3. Privacy Policy
  [PASS] 4. Return Policy
  [PASS] 5. FAQs
  [PASS] 6. Social Handles
  [PASS] 7. Contact Info
  [PASS] 8. Brand Context
  [PASS] 9. Important Links
```

## How It Works

The implementation uses a working scraper (`working_scraper.py`) that:

1. **Fetches Homepage** - Gets the main page HTML
2. **Detects Shopify** - Checks for Shopify markers
3. **Gets Products** - Fetches from `/products.json` endpoint
4. **Extracts Hero Products** - Finds featured products on homepage
5. **Fetches Policies** - Gets privacy, return, shipping policies
6. **Extracts FAQs** - Parses FAQ pages or schema
7. **Finds Social Links** - Uses regex to find social media
8. **Gets Contact Info** - Extracts emails and phone numbers
9. **Fetches Brand Context** - Gets about/story pages
10. **Extracts Important Links** - Finds tracking, support, blog links

## Test Stores

You can test with these verified Shopify stores:
- `https://memy.co.in` - Fashion (India)
- `https://colourpop.com` - Cosmetics (USA)
- `https://jeffreestarcosmetics.com` - Beauty
- `https://gymshark.com` - Fitness
- `https://allbirds.com` - Footwear

## Troubleshooting

### Server won't start
```bash
# Check Python version (needs 3.11+)
python --version

# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### No data extracted
- Verify the URL is a Shopify store
- Check internet connection
- Try a different test store

### Import errors
```bash
# Make sure you're in the project directory
cd shopify-insights-fetcher

# Reinstall packages
pip install --force-reinstall -r requirements.txt
```

## API Status Codes

- **200**: Success - All data extracted
- **404**: Website not found
- **422**: Invalid URL format
- **500**: Internal server error

## Performance

Typical extraction times:
- Small stores: 5-10 seconds
- Medium stores: 10-20 seconds
- Large stores: 20-30 seconds

## Bonus Features

### MySQL Database (Optional)
If MySQL is configured in `.env`, data will be automatically saved to database.

### Competitor Analysis
The `/api/version1/competitors` endpoint finds and analyzes competitor stores.

## Success Criteria Met

✓ All 9 mandatory data points extracted
✓ Proper error handling (404, 500 status codes)
✓ Clean code with SOLID principles
✓ Pydantic models for validation
✓ Postman-compatible API
✓ Bonus: Competitor analysis
✓ Bonus: Database persistence ready

## Next Steps

1. Deploy to Google Cloud Run:
```bash
gcloud run deploy shopify-insights-api --source . --port 8080
```

2. Run with Docker:
```bash
docker build -t shopify-insights .
docker run -p 8080:8080 shopify-insights
```

The implementation is complete and ready for production use!