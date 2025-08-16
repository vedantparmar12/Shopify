@echo off
echo ======================================
echo Shopify Insights Fetcher - Startup
echo ======================================

REM Check if virtual environment exists
if not exist ".venv" (
    if not exist "venv" (
        echo Creating virtual environment...
        python -m venv .venv
        call .venv\Scripts\activate
    ) else (
        call venv\Scripts\activate
    )
) else (
    call .venv\Scripts\activate
)

REM Install dependencies if needed
echo Checking dependencies...
pip install -q -r requirements.txt

REM Start the server
echo.
echo Starting FastAPI server...
echo ======================================
echo.
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload