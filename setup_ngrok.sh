#!/bin/bash
echo "🌐 Setting up ngrok tunnel for webhook"
echo "======================================"

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed"
    echo "📥 Please install ngrok:"
    echo "   1. Go to https://ngrok.com/download"
    echo "   2. Download and install ngrok"
    echo "   3. Sign up for free account"
    echo "   4. Run: ngrok authtoken YOUR_TOKEN"
    exit 1
fi

echo "🚀 Starting ngrok tunnel on port 8080..."
echo "📡 Your webhook URL will be: https://RANDOM.ngrok.io/gmail-webhook"
echo "🔧 Update WEBHOOK_URL in .env with the ngrok URL"
echo ""
echo "⚠️  Keep this terminal open while testing push notifications!"
echo ""

# Start ngrok tunnel
ngrok http 8080
