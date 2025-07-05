# setup_push_notifications.py - Setup Gmail push notifications for a user
import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.cloud import pubsub_v1
from googleapiclient.discovery import build
from push_notification_system import PushNotificationSetup, PushNotificationConfig

def setup_google_cloud_pubsub():
    """Set up Google Cloud Pub/Sub topic and subscription"""
    load_dotenv()
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID", "robust-metrics-465003-n0")
    topic_name = os.getenv("PUBSUB_TOPIC_NAME", "gmail-notifications")
    subscription_name = os.getenv("PUBSUB_SUBSCRIPTION_NAME", "gmail-notifications-sub")
    webhook_url = os.getenv("WEBHOOK_URL", "https://your-domain.com/gmail-webhook")
    
    print("🔧 Setting up Google Cloud Pub/Sub")
    print(f"Project ID: {project_id}")
    print(f"Topic: {topic_name}")
    print(f"Subscription: {subscription_name}")
    print(f"Webhook URL: {webhook_url}")
    
    try:
        # Initialize Pub/Sub client
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
        
        print("✅ Pub/Sub setup complete!")
        return True
        
    except Exception as e:
        print(f"❌ Pub/Sub setup failed: {e}")
        print("\n📋 Manual setup required:")
        print(f"1. Go to Google Cloud Console: https://console.cloud.google.com/")
        print(f"2. Enable Pub/Sub API")
        print(f"3. Create topic: {topic_name}")
        print(f"4. Create push subscription with endpoint: {webhook_url}")
        return False

def setup_user_push_notifications(user_email: str):
    """Set up push notifications for a specific user"""
    print(f"\n🔐 Setting up push notifications for: {user_email}")
    
    try:
        # OAuth flow for user
        scopes = ['https://www.googleapis.com/auth/gmail.readonly', 
                 'https://www.googleapis.com/auth/gmail.modify']
        
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes)
        credentials = flow.run_local_server(port=8080, access_type='offline')
        
        print("✅ User authentication successful")
        
        # Set up push notifications
        setup = PushNotificationSetup()
        result = setup.setup_complete_system(user_email, credentials)
        
        if result['success']:
            print("✅ Push notifications setup successful!")
            print("\n📧 What happens now:")
            print("  • Gmail will send notifications when new emails arrive")
            print("  • Your webhook server will receive these notifications")
            print("  • New emails will be automatically classified and labeled")
            print("  • Thread-based classification will be applied")
            
            return True
        else:
            print(f"❌ Setup failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ User setup failed: {e}")
        return False

def create_environment_file():
    """Create sample .env file with required variables"""
    env_content = """# Gmail Push Notifications Configuration

# Google Cloud Project
GOOGLE_CLOUD_PROJECT_ID=robust-metrics-465003-n0

# Pub/Sub Configuration
PUBSUB_TOPIC_NAME=gmail-notifications
PUBSUB_SUBSCRIPTION_NAME=gmail-notifications-sub

# Webhook Configuration
WEBHOOK_URL=https://your-domain.com/gmail-webhook
WEBHOOK_SECRET=your-secure-webhook-secret

# Flask Server Configuration
FLASK_PORT=8080
FLASK_HOST=0.0.0.0

# API Keys
OPENAI_API_KEY=your_openai_api_key
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json

# Optional: Pinecone (if using vector storage)
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=us-west1-gcp
PINECONE_INDEX_NAME=email-context
"""
    
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Created .env file template")
        print("📝 Please update .env with your actual values")
    else:
        print("ℹ️  .env file already exists")

def main():
    """Main setup function"""
    print("🚀 Gmail Push Notification Setup")
    print("=" * 40)
    
    # Create environment file template
    create_environment_file()
    
    print("\n📋 Setup Steps:")
    print("1. Set up Google Cloud Pub/Sub")
    print("2. Set up user push notifications")
    print("3. Start the webhook server")
    
    # Step 1: Set up Pub/Sub
    print(f"\n{'='*40}")
    print("STEP 1: Google Cloud Pub/Sub Setup")
    print(f"{'='*40}")
    
    pubsub_success = setup_google_cloud_pubsub()
    
    if not pubsub_success:
        print("⚠️  Pub/Sub setup incomplete. Please complete manually before proceeding.")
        return
    
    # Step 2: Set up user notifications
    print(f"\n{'='*40}")
    print("STEP 2: User Push Notifications Setup")
    print(f"{'='*40}")
    
    user_email = input("Enter user email to setup notifications: ").strip()
    if not user_email:
        print("❌ No email provided")
        return
    
    user_success = setup_user_push_notifications(user_email)
    
    if not user_success:
        print("⚠️  User setup incomplete.")
        return
    
    # Step 3: Instructions for webhook server
    print(f"\n{'='*40}")
    print("STEP 3: Start Webhook Server")
    print(f"{'='*40}")
    
    print("✅ Setup complete! Next steps:")
    print("\n🚀 To start the webhook server:")
    print("   python3 push_notification_system.py")
    print("\n🌐 Make sure your webhook URL is accessible from the internet")
    print("   Use ngrok for testing: ngrok http 8080")
    print("\n📧 New emails will now be automatically labeled!")
    
    print(f"\n📊 System Overview:")
    print("   📩 New email arrives → Gmail sends push notification")
    print("   🔄 Webhook receives notification → Fetches email")
    print("   🧵 Email classified as part of thread")
    print("   🏷️  Thread label applied automatically")
    print("   ✅ Process complete in real-time!")

if __name__ == "__main__":
    main()  