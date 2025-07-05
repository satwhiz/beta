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
