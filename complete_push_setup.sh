# Complete Push Notification Setup Script
# Run this from your project root directory (v0.0/)

echo "🚀 Setting up Gmail Push Notification System"
echo "============================================="

# Step 1: Create push_system.py in project root
echo "📁 Creating push_system.py in project root..."

# Step 2: Update .env with required variables
echo "🔧 Updating .env file..."
cat >> .env << 'ENV_EOF'

# Gmail Push Notification Settings
GOOGLE_CLOUD_PROJECT_ID=robust-metrics-465003-n0
PUBSUB_TOPIC_NAME=gmail-notifications
PUBSUB_SUBSCRIPTION_NAME=gmail-notifications-sub
WEBHOOK_URL=https://your-domain.ngrok.io/gmail-webhook
WEBHOOK_SECRET=your-secure-webhook-secret-key
FLASK_PORT=8080
FLASK_HOST=0.0.0.0
ENV_EOF

# Step 3: Install additional requirements for push notifications
echo "📦 Installing push notification requirements..."
pip install flask google-cloud-pubsub google-cloud-core

# Step 4: Create ngrok setup script
cat > setup_ngrok.sh << 'NGROK_EOF'
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
NGROK_EOF

chmod +x setup_ngrok.sh

# Step 5: Create Google Cloud setup script
cat > setup_google_cloud.py << 'GCP_EOF'
#!/usr/bin/env python3
"""
Google Cloud Setup for Gmail Push Notifications
Run this script to setup Google Cloud Pub/Sub
"""

import os
from google.cloud import pubsub_v1
from dotenv import load_dotenv

def setup_pubsub():
    """Setup Google Cloud Pub/Sub topic and subscription"""
    load_dotenv()
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    topic_name = os.getenv("PUBSUB_TOPIC_NAME", "gmail-notifications") 
    subscription_name = os.getenv("PUBSUB_SUBSCRIPTION_NAME", "gmail-notifications-sub")
    webhook_url = os.getenv("WEBHOOK_URL")
    
    print(f"🔧 Setting up Google Cloud Pub/Sub")
    print(f"Project: {project_id}")
    print(f"Topic: {topic_name}")
    print(f"Subscription: {subscription_name}")
    print(f"Webhook: {webhook_url}")
    
    try:
        # Initialize clients
        publisher = pubsub_v1.PublisherClient()
        subscriber = pubsub_v1.SubscriberClient()
        
        # Create topic
        topic_path = publisher.topic_path(project_id, topic_name)
        
        try:
            topic = publisher.create_topic(request={"name": topic_path})
            print(f"✅ Created topic: {topic.name}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"✅ Topic already exists: {topic_path}")
            else:
                raise
        
        # Create subscription
        subscription_path = subscriber.subscription_path(project_id, subscription_name)
        push_config = pubsub_v1.PushConfig(push_endpoint=webhook_url)
        
        try:
            subscription = subscriber.create_subscription(
                request={
                    "name": subscription_path,
                    "topic": topic_path,
                    "push_config": push_config,
                }
            )
            print(f"✅ Created subscription: {subscription.name}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"✅ Subscription already exists: {subscription_path}")
            else:
                raise
        
        print(f"\n🎉 Google Cloud Pub/Sub setup complete!")
        return True
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        print(f"\n📋 Manual setup required:")
        print(f"1. Install Google Cloud SDK: https://cloud.google.com/sdk/docs/install")
        print(f"2. Run: gcloud auth application-default login")
        print(f"3. Enable Pub/Sub API in Google Cloud Console")
        print(f"4. Create topic and subscription manually")
        return False

if __name__ == "__main__":
    setup_pubsub()
GCP_EOF

# Step 6: Create quick start script
cat > start_push_system.py << 'START_EOF'
#!/usr/bin/env python3
"""
Quick Start Script for Gmail Push Notifications
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

def check_requirements():
    """Check if all requirements are met"""
    load_dotenv()
    
    print("🔍 Checking push notification requirements...")
    
    # Check environment variables
    required_vars = [
        "GOOGLE_CLOUD_PROJECT_ID",
        "WEBHOOK_URL", 
        "OPENAI_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        print(f"📝 Please update your .env file")
        return False
    
    # Check if credentials.json exists
    if not os.path.exists("credentials.json"):
        print("❌ credentials.json not found")
        print("📥 Please download from Google Cloud Console")
        return False
    
    # Check if ngrok URL is set
    webhook_url = os.getenv("WEBHOOK_URL")
    if "your-domain" in webhook_url or "ngrok" not in webhook_url:
        print("⚠️  WEBHOOK_URL needs to be updated with your ngrok URL")
        print("🌐 Run: ./setup_ngrok.sh to get your ngrok URL")
        print("📝 Then update WEBHOOK_URL in .env")
        return False
    
    print("✅ All requirements met!")
    return True

def main():
    """Main function"""
    print("🚀 Gmail Push Notification Quick Start")
    print("=====================================")
    
    if not check_requirements():
        print("\n❌ Setup incomplete. Please fix the issues above.")
        return
    
    print("\n🎯 Starting push notification system...")
    
    try:
        # Import and run push system
        from push_system import PushNotificationServer
        
        server = PushNotificationServer()
        server.run()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("📁 Make sure push_system.py is in the current directory")
    except KeyboardInterrupt:
        print("\n👋 Push notification system stopped")

if __name__ == "__main__":
    main()
START_EOF

echo ""
echo "✅ Push notification setup files created!"
echo ""
echo "📋 Next steps:"
echo "1. 🔧 Run: python setup_google_cloud.py"
echo "2. 🌐 Run: ./setup_ngrok.sh (in separate terminal)"
echo "3. 📝 Update WEBHOOK_URL in .env with ngrok URL"
echo "4. 🚀 Run: python start_push_system.py"
echo ""
echo "📖 For detailed instructions, see the setup guide below."