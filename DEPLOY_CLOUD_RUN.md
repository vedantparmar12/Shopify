# Google Cloud Run Deployment Guide

## Prerequisites
- Google Cloud Project with billing enabled
- gcloud CLI installed and configured
- Docker installed locally (optional for local testing)

## Quick Deploy from GitHub

### 1. Clone and Deploy
```bash
# Clone the repository
git clone https://github.com/your-username/shopify-insights-fetcher.git
cd shopify-insights-fetcher

# Set your project ID
export PROJECT_ID=your-gcp-project-id
export SERVICE_NAME=shopify-insights-api
export REGION=us-central1

# Configure gcloud
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.api
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Build and deploy in one command
gcloud run deploy $SERVICE_NAME \
  --source . \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 60 \
  --max-instances 10 \
  --port 8080
```

### 2. Set Environment Variables
```bash
# Set environment variables for the deployed service
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --set-env-vars "DATABASE_URL=mysql://user:pass@host:3306/db" \
  --set-env-vars "ENVIRONMENT=production" \
  --set-env-vars "DEBUG=False" \
  --set-env-vars "REQUEST_TIMEOUT=30" \
  --set-env-vars "MAX_PRODUCTS=100"
```

## Alternative: Deploy with Pre-built Image

### 1. Build Docker Image Locally
```bash
# Build the image
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME:latest .

# Test locally (optional)
docker run -p 8080:8080 -e PORT=8080 gcr.io/$PROJECT_ID/$SERVICE_NAME:latest

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:latest
```

### 2. Deploy to Cloud Run
```bash
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 60 \
  --max-instances 10
```

## Using Cloud SQL (MySQL) - Optional

### 1. Create Cloud SQL Instance
```bash
# Create MySQL instance
gcloud sql instances create shopify-mysql \
  --database-version=MYSQL_8_0 \
  --tier=db-f1-micro \
  --region=$REGION

# Create database
gcloud sql databases create shopify_insights \
  --instance=shopify-mysql

# Create user
gcloud sql users create shopify_admin \
  --instance=shopify-mysql \
  --password=YourStrongPassword123
```

### 2. Connect Cloud Run to Cloud SQL
```bash
# Get connection name
export CONNECTION_NAME=$(gcloud sql instances describe shopify-mysql --format='get(connectionName)')

# Update service with Cloud SQL connection
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --add-cloudsql-instances $CONNECTION_NAME \
  --set-env-vars "DATABASE_URL=mysql://shopify_admin:YourStrongPassword123@localhost/shopify_insights?unix_socket=/cloudsql/$CONNECTION_NAME"
```

## Continuous Deployment from GitHub

### 1. Set up Cloud Build Trigger
```bash
# Connect GitHub repository
gcloud builds repositories create shopify-insights-repo \
  --remote-uri=https://github.com/your-username/shopify-insights-fetcher.git \
  --connection=your-connection-name \
  --region=$REGION

# Create trigger for main branch
gcloud builds triggers create github \
  --repo-name=shopify-insights-repo \
  --repo-owner=your-username \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

### 2. Create cloudbuild.yaml
Create this file in your repository root:

```yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/shopify-insights-api:$COMMIT_SHA', '.']
  
  # Push the container image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/shopify-insights-api:$COMMIT_SHA']
  
  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'shopify-insights-api'
      - '--image'
      - 'gcr.io/$PROJECT_ID/shopify-insights-api:$COMMIT_SHA'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'

images:
  - 'gcr.io/$PROJECT_ID/shopify-insights-api:$COMMIT_SHA'
```

## Testing the Deployment

### 1. Get Service URL
```bash
export SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
echo "Service URL: $SERVICE_URL"
```

### 2. Test API Endpoints
```bash
# Test health check
curl $SERVICE_URL/

# Test extraction endpoint
curl -X POST $SERVICE_URL/api/version1/extract \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://memy.co.in"}'

# Test competitor analysis
curl -X POST $SERVICE_URL/api/version1/competitors \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://colourpop.com", "find_competitors": true, "max_competitors": 3}'
```

## Monitoring and Logs

### View Logs
```bash
gcloud run services logs read $SERVICE_NAME --region $REGION --limit 50
```

### View Metrics
```bash
# Open Cloud Console
gcloud app browse
# Navigate to Cloud Run > Your Service > Metrics
```

## Cost Optimization

### Set Minimum Instances to 0
```bash
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --min-instances 0
```

### Set Concurrency
```bash
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --concurrency 80
```

## Cleanup

### Delete Service
```bash
gcloud run services delete $SERVICE_NAME --region $REGION
```

### Delete Cloud SQL Instance (if created)
```bash
gcloud sql instances delete shopify-mysql
```

## Estimated Costs
- Cloud Run: ~$0.00002400 per vCPU-second, ~$0.00000250 per GiB-second
- Cloud SQL: ~$7.67/month for db-f1-micro
- Network: $0.12 per GB egress

For typical usage (1000 requests/day, 10s per request):
- Estimated monthly cost: < $5 without database
- With Cloud SQL: ~$13/month

## Troubleshooting

### Service not starting
Check logs: `gcloud run services logs read $SERVICE_NAME --region $REGION`

### Memory issues
Increase memory: `gcloud run services update $SERVICE_NAME --memory 2Gi`

### Timeout issues
Increase timeout: `gcloud run services update $SERVICE_NAME --timeout 300`

### Database connection issues
Ensure Cloud SQL proxy is configured correctly and connection string is proper.