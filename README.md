# Shopify Store Insights Fetcher

A Python application that extracts and organizes brand insights from Shopify store websites without using the official Shopify API.

## Features

### Core Features
- Extracts 9 mandatory data points from Shopify stores
  - Product catalog and hero products
  - Privacy and return/refund policies
  - Brand context and FAQs
  - Social media handles
  - Contact information
  - Important links
- RESTful API with proper error handling (401, 500 status codes)
- Async processing with aiohttp
- Pydantic models for data validation

### Bonus Features
- Competitor analysis
- MySQL database persistence
- Redis caching (optional)

## Technology Stack

- Language: Python 3.11
- Framework: FastAPI
- Database: MySQL
- Cache: Redis (optional)
- Web Scraping: aiohttp, BeautifulSoup4

## Installation

### Prerequisites
- Python 3.9+
- MySQL (optional)
- Redis (optional)

### Local Development Setup

1. **Clone the repository**
```bash
cd shopify-insights-fetcher
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Run the application**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Access the Application
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs

## API Documentation

### Main Endpoints

#### Extract Brand Insights
```http
POST /api/v1/extract
Content-Type: application/json

{
  "website_url": "https://memy.co.in"
}
```

**Response**: Complete BrandInsights object with all extracted data

#### Competitor Analysis (Bonus Feature)
```http
POST /api/v1/competitors
Content-Type: application/json

{
  "website_url": "https://store.com",
  "find_competitors": true,
  "max_competitors": 5
}
```

### Status Codes
- `200`: Success
- `401`: Website not found
- `422`: Invalid URL format
- `429`: Rate limit exceeded
- `500`: Internal server error

## Data Models

### BrandInsights Schema
```python
{
  "website_url": "string",
  "brand_name": "string",
  "product_catalog": [...],
  "hero_products": [...],
  "privacy_policy": "string",
  "return_refund_policy": "string",
  "brand_context": "string",
  "faqs": [...],
  "social_handles": [...],
  "contact_info": {...},
  "important_links": [...],
  "extraction_timestamp": "datetime",
  "extraction_success": "boolean"
}
```

## Configuration

### Environment Variables
```env
# Database
DATABASE_URL=mysql://user:password@localhost:3306/shopify_insights
REDIS_URL=redis://localhost:6379

# LLM Service (optional)
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_key

# Rate Limiting
REQUESTS_PER_MINUTE=60
CONCURRENT_REQUESTS=10

# Scraping
USER_AGENT=ShopifyInsightsFetcher/1.0
REQUEST_TIMEOUT=30
```

## Testing

```bash
python -m pytest
```

## Configuration

See `.env.example` for configuration options.

## Reference Shopify Stores for Testing

- memy.co.in
- hairoriginals.com
- colourpop.com
- fashionnova.com
- gymshark.com
- allbirds.com
- kith.com

