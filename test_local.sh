#!/bin/bash
# Local testing script for the newspaper automation

echo "🔧 E-Newspaper Automation - Local Test"
echo "======================================"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo ""
    echo "🔴 IMPORTANT: Edit .env file and add your Discord webhook URL"
    echo "   Then run this script again."
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check if Discord webhook is configured
if [ -z "$DISCORD_WEBHOOK_URL" ] || [ "$DISCORD_WEBHOOK_URL" = "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL_HERE" ]; then
    echo "❌ Discord webhook URL not configured in .env file"
    exit 1
fi

echo "✅ Discord webhook configured"

# Check for Chrome (macOS)
if command -v google-chrome &> /dev/null || command -v "Google Chrome" &> /dev/null || [ -d "/Applications/Google Chrome.app" ]; then
    echo "✅ Chrome found"
else
    echo "⚠️  Chrome not found - you may need to install it"
    echo "   Download from: https://www.google.com/chrome/"
fi

# Run the scraper
echo ""
echo "🚀 Running newspaper automation..."
echo "======================================"
python3 scraper.py

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Automation completed successfully!"
    echo "📁 Check the e-paper/ folder for downloaded PDFs"
    echo "📊 Check download_history.json for processing history"
else
    echo ""
    echo "❌ Automation failed - check logs above"
    exit 1
fi
