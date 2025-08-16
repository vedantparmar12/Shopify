# Quick Deployment Guide

## Deploy to Google Cloud Run (Recommended)

### One Command Deploy
```bash
# Clone and deploy
git clone https://github.com/your-repo/shopify-insights-fetcher.git
cd shopify-insights-fetcher

# Deploy to Cloud Run
gcloud run deploy shopify-insights-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080
```

The service will be available at the URL shown after deployment.

## Local Docker Run

### Build and Run
```bash
# Build image
docker build -t shopify-insights .

# Run container
docker run -p 8080:8080 -e PORT=8080 shopify-insights
```

Access at: http://localhost:8080

## Environment Variables (Optional)

Set these in Cloud Run or Docker:
- `DATABASE_URL`: MySQL connection string (optional)
- `REQUEST_TIMEOUT`: API timeout in seconds (default: 30)
- `MAX_PRODUCTS`: Max products to fetch (default: 100)

## Test the API

### Extract Insights
```bash
curl -X POST http://your-url:8080/api/version1/extract \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://memy.co.in"}'
```

### Find Competitors
```bash
curl -X POST http://your-url:8080/api/version1/competitors \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://colourpop.com", "find_competitors": true}'
```

## API Documentation

Once deployed, visit:
- Swagger UI: `http://your-url/docs`
- ReDoc: `http://your-url/redoc`