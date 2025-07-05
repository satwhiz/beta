#!/usr/bin/env python3
"""
Fixed Google Cloud Setup for Gmail Push Notifications
"""

import os
from google.cloud import pubsub_v1
from google.cloud.pubsub_v1.types import PushConfig
from dotenv import load_dotenv

def setup_pubsub():
    """Setup Google Cloud Pub/Sub topic and subscription with fixed imports"""
    load_dotenv()
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    topic_name = os.getenv("PUBSUB_TOPIC_NAME", "gmail-notifications") 
    subscription_name = os.getenv("PUBSUB_SUBSCRIPTION_NAME", "gmail-notifications-sub")
    webhook_url = os.getenv("WEBHOOK_URL")
    
    print(f"🔧 Setting up Google Cloud Pub/Sub (Fixed Version)")
    print(f"Project: {project_id}")
    print(f"Topic: {topic_name}")
    print(f"Subscription: {subscription_name}")
    print(f"Webhook: {webhook_url}")
    
    if not webhook_url or "your-domain" in webhook_url:
        print("❌ WEBHOOK_URL not properly set in .env")
        print("🌐 Please run ngrok and update WEBHOOK_URL in .env")
        return False
    
    try:
        # Initialize clients
        publisher = pubsub_v1.PublisherClient()
        subscriber = pubsub_v1.SubscriberClient()
        
        # Create topic (already exists based on your output)
        topic_path = publisher.topic_path(project_id, topic_name)
        print(f"✅ Topic confirmed: {topic_path}")
        
        # Create subscription with proper PushConfig import
        subscription_path = subscriber.subscription_path(project_id, subscription_name)
        
        # Use the correct PushConfig from types
        push_config = PushConfig(push_endpoint=webhook_url)
        
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
                
                # Update existing subscription with new webhook URL
                try:
                    subscriber.modify_push_config(
                        request={
                            "subscription": subscription_path,
                            "push_config": push_config,
                        }
                    )
                    print(f"✅ Updated subscription webhook URL")
                except Exception as update_error:
                    print(f"⚠️ Could not update webhook URL: {update_error}")
            else:
                raise
        
        print(f"\n🎉 Google Cloud Pub/Sub setup complete!")
        print(f"📡 Webhook endpoint: {webhook_url}")
        print(f"🔔 Gmail push notifications ready!")
        
        return True
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        print(f"\n🔧 Alternative: Manual setup via Google Cloud Console")
        return False

def test_webhook_connectivity():
    """Test if the webhook URL is accessible"""
    import requests
    
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url or "your-domain" in webhook_url:
        print("⚠️ Webhook URL not set properly")
        return False
    
    try:
        # Test if ngrok tunnel is working
        health_url = webhook_url.replace('/gmail-webhook', '/health')
        print(f"🔍 Testing webhook connectivity: {health_url}")
        
        response = requests.get(health_url, timeout=5)
        if response.status_code == 200:
            print("✅ Webhook is accessible")
            return True
        else:
            print(f"⚠️ Webhook returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Webhook not accessible: {e}")
        print("🌐 Make sure ngrok is running: ngrok http 8080")
        return False

def main():
    """Main setup function"""
    print("🚀 Gmail Push Notification Setup (Fixed)")
    print("=" * 50)
    
    # Load environment
    load_dotenv()
    
    # Check basic requirements
    if not os.getenv("GOOGLE_CLOUD_PROJECT_ID"):
        print("❌ GOOGLE_CLOUD_PROJECT_ID not set in .env")
        return
    
    if not os.getenv("WEBHOOK_URL") or "your-domain" in os.getenv("WEBHOOK_URL"):
        print("❌ WEBHOOK_URL not properly set in .env")
        print("🔧 Steps to fix:")
        print("   1. Run: ngrok http 8080")
        print("   2. Copy the https://xxxxx.ngrok.io URL")
        print("   3. Update .env: WEBHOOK_URL=https://xxxxx.ngrok.io/gmail-webhook")
        return
    
    # Test webhook connectivity first
    print("🔍 Testing webhook connectivity...")
    webhook_ok = test_webhook_connectivity()
    
    if not webhook_ok:
        print("⚠️ Webhook not accessible. Push notifications may not work.")
        proceed = input("Continue with Pub/Sub setup anyway? (y/N): ")
        if proceed.lower() != 'y':
            return
    
    # Setup Pub/Sub
    success = setup_pubsub()
    
    if success:
        print(f"\n✅ Setup completed successfully!")
        print(f"🚀 Ready to start push notification system:")
        print(f"   python push_system.py")
    else:
        print(f"\n❌ Setup failed. Try manual setup or use simple monitoring instead.")
        print(f"🔧 Alternative: python simple_monitor.py")

if __name__ == "__main__":
    main()