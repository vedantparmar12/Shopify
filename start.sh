#!/bin/bash

# Startup script for Shopify Insights Fetcher

echo "======================================"
echo "Shopify Insights Fetcher - Startup"
echo "======================================"

# Check if virtual environment exists
if [ ! -d ".venv" ] && [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
else
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    else
        source venv/bin/activate
    fi
fi

# Install dependencies if needed
echo "Checking dependencies..."
pip install -q -r requirements.txt

# Start the server
echo ""
echo "Starting FastAPI server..."
echo "======================================"
echo ""
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload