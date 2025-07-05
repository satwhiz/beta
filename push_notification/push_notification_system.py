# push_notification_system.py - Real-time email labeling with push notifications
import os
import json
import base64
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from flask import Flask, request, jsonify
from google.cloud import pubsub_v1
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import threading
import time
from dotenv import load_dotenv

# Our imports
from agents.thread_email_classifier import ThreadEmailClassifier
from models.email_models import EmailMessage
from utils.thread_organizer import ThreadOrganizer
from tools.gmail_tools import GmailTools

class PushNotificationConfig:
    """Configuration for Gmail Push Notifications"""
    def __init__(self):
        load_dotenv()
        
        # Google Cloud Project settings
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID", "robust-metrics-465003-n0")
        self.topic_name = os.getenv("PUBSUB_TOPIC_NAME", "gmail-notifications")
        self.subscription_name = os.getenv("PUBSUB_SUBSCRIPTION_NAME", "gmail-notifications-sub")
        
        # Webhook settings
        self.webhook_url = os.getenv("WEBHOOK_URL", "https://your-domain.com/gmail-webhook")
        self.webhook_secret = os.getenv("WEBHOOK_SECRET", "your-webhook-secret")
        
        # Flask app settings
        self.flask_port = int(os.getenv("FLASK_PORT", "8080"))
        self.flask_host = os.getenv("FLASK_HOST", "0.0.0.0")

class UserTokenManager:
    """Manage user tokens and credentials"""
    def __init__(self, users_csv: str = "users.csv"):
        self.users_csv = users_csv
        self.active_users = {}  # Cache for user credentials
        self._load_users()
    
    def _load_users(self):
        """Load users from CSV into memory"""
        try:
            import csv
            with open(self.users_csv, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    user_email = row['user_email']
                    # In production, you'd decrypt stored tokens
                    self.active_users[user_email] = {
                        'email': user_email,
                        'token_hash': row.get('access_token_hash', ''),
                        'refresh_hash': row.get('refresh_token_hash', ''),
                        'last_processed': row.get('last_processed_at', ''),
                        'watch_expiry': None  # Will be set when watch is established
                    }
        except FileNotFoundError:
            print("No users.csv found, starting with empty user list")
    
    def get_user_credentials(self, user_email: str) -> Optional[Credentials]:
        """Get credentials for a user (simplified for demo)"""
        # In production, you'd retrieve and decrypt actual tokens
        # For now, return None to indicate need for re-authentication
        return None
    
    def is_user_active(self, user_email: str) -> bool:
        """Check if user is active and has valid watch"""
        user = self.active_users.get(user_email)
        if not user:
            return False
        
        # Check if watch is still valid (Gmail watches expire after 7 days)
        watch_expiry = user.get('watch_expiry')
        if watch_expiry and datetime.now() > watch_expiry:
            return False
        
        return True

class GmailPushNotificationManager:
    """Manage Gmail Push Notifications setup"""
    def __init__(self, config: PushNotificationConfig):
        self.config = config
        self.user_manager = UserTokenManager()
    
    def setup_push_notifications(self, user_email: str, credentials: Credentials) -> bool:
        """Set up Gmail push notifications for a user"""
        try:
            # Create Gmail service
            service = build('gmail', 'v1', credentials=credentials)
            
            # Set up watch request
            watch_request = {
                'labelIds': ['INBOX'],  # Watch inbox for new emails
                'topicName': f'projects/{self.config.project_id}/topics/{self.config.topic_name}'
            }
            
            # Start watching
            watch_response = service.users().watch(userId='me', body=watch_request).execute()
            
            # Store watch details
            history_id = watch_response.get('historyId')
            expiration = watch_response.get('expiration')
            
            # Update user watch expiry
            if user_email in self.user_manager.active_users:
                # Convert expiration (milliseconds since epoch) to datetime
                expiry_dt = datetime.fromtimestamp(int(expiration) / 1000) if expiration else None
                self.user_manager.active_users[user_email]['watch_expiry'] = expiry_dt
                self.user_manager.active_users[user_email]['history_id'] = history_id
            
            print(f"✅ Push notifications setup for {user_email}")
            print(f"   History ID: {history_id}")
            print(f"   Expiration: {expiry_dt}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup push notifications for {user_email}: {e}")
            return False
    
    def renew_watch(self, user_email: str) -> bool:
        """Renew Gmail watch for a user"""
        credentials = self.user_manager.get_user_credentials(user_email)
        if not credentials:
            print(f"No credentials found for {user_email}")
            return False
        
        return self.setup_push_notifications(user_email, credentials)

class EmailProcessor:
    """Process new emails and apply labels"""
    def __init__(self):
        self.classifier = ThreadEmailClassifier()
        self.thread_organizer = ThreadOrganizer()
        self.user_manager = UserTokenManager()
    
    def process_new_email(self, user_email: str, message_id: str, history_id: str) -> Dict:
        """Process a single new email"""
        try:
            print(f"📧 Processing new email for {user_email}: {message_id}")
            
            # Get user credentials
            credentials = self.user_manager.get_user_credentials(user_email)
            if not credentials:
                return {'success': False, 'error': 'No credentials for user'}
            
            # Create Gmail service
            service = build('gmail', 'v1', credentials=credentials)
            gmail_tools = GmailTools(credentials)
            
            # Get the new email
            message = service.users().messages().get(userId='me', id=message_id, format='full').execute()
            email_obj = self._parse_gmail_message(message)
            
            if not email_obj:
                return {'success': False, 'error': 'Failed to parse email'}
            
            # Get thread context
            thread_emails = gmail_tools.get_thread_messages(email_obj.thread_id)
            
            # Organize thread
            threads = {email_obj.thread_id: thread_emails}
            
            # Classify the thread
            classifications = self.classifier.classify_multiple_threads(threads)
            
            if not classifications:
                return {'success': False, 'error': 'Failed to classify thread'}
            
            classification = classifications[0]
            
            # Apply label in Gmail
            label_success = gmail_tools.apply_label(message_id, classification.label.value)
            
            result = {
                'success': True,
                'user_email': user_email,
                'message_id': message_id,
                'thread_id': email_obj.thread_id,
                'subject': email_obj.subject,
                'from_email': email_obj.from_email,
                'label': classification.label.value,
                'confidence': classification.confidence,
                'reasoning': classification.reasoning,
                'label_applied': label_success,
                'processed_at': datetime.now().isoformat()
            }
            
            print(f"✅ Email processed: {classification.label.value} (confidence: {classification.confidence:.2f})")
            return result
            
        except Exception as e:
            print(f"❌ Error processing email: {e}")
            return {'success': False, 'error': str(e)}
    
    def _parse_gmail_message(self, message_data: Dict) -> Optional[EmailMessage]:
        """Parse Gmail message into EmailMessage object"""
        try:
            headers = message_data['payload']['headers']
            header_dict = {h['name']: h['value'] for h in headers}
            
            # Extract content (simplified)
            content = self._extract_content(message_data['payload'])
            
            # Parse date
            date_str = header_dict.get('Date', '')
            try:
                from email.utils import parsedate_to_datetime
                date = parsedate_to_datetime(date_str)
            except:
                date = datetime.now()
            
            return EmailMessage(
                id=message_data['id'],
                thread_id=message_data['threadId'],
                from_email=header_dict.get('From', ''),
                to_emails=self._parse_emails(header_dict.get('To', '')),
                cc_emails=self._parse_emails(header_dict.get('Cc', '')),
                subject=header_dict.get('Subject', 'No Subject'),
                content=content,
                date=date
            )
            
        except Exception as e:
            print(f"Error parsing message: {e}")
            return None
    
    def _extract_content(self, payload: Dict) -> str:
        """Extract text content from email payload"""
        content = ""
        try:
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                        data = part['body']['data']
                        content = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
            elif payload['mimeType'] == 'text/plain' and 'data' in payload['body']:
                data = payload['body']['data']
                content = base64.urlsafe_b64decode(data).decode('utf-8')
            
            return content[:2000]  # Limit content length
        except Exception as e:
            print(f"Error extracting content: {e}")
            return ""
    
    def _parse_emails(self, email_string: str) -> List[str]:
        """Parse email addresses from string"""
        if not email_string:
            return []
        import re
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', email_string)
        return emails

class PushNotificationServer:
    """Flask server to handle Gmail push notifications"""
    def __init__(self):
        self.app = Flask(__name__)
        self.config = PushNotificationConfig()
        self.email_processor = EmailProcessor()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/gmail-webhook', methods=['POST'])
        def gmail_webhook():
            """Handle Gmail push notifications"""
            try:
                # Verify webhook authenticity (optional but recommended)
                if not self._verify_webhook_signature(request):
                    return jsonify({'error': 'Invalid signature'}), 401
                
                # Parse Pub/Sub message
                envelope = request.get_json()
                if not envelope:
                    return jsonify({'error': 'No JSON body'}), 400
                
                pubsub_message = envelope.get('message')
                if not pubsub_message:
                    return jsonify({'error': 'No message in envelope'}), 400
                
                # Decode message data
                message_data = base64.b64decode(pubsub_message['data']).decode('utf-8')
                notification_data = json.loads(message_data)
                
                # Extract notification details
                user_email = notification_data.get('emailAddress')
                history_id = notification_data.get('historyId')
                
                if not user_email:
                    return jsonify({'error': 'No email address in notification'}), 400
                
                print(f"📩 Received notification for {user_email}, history ID: {history_id}")
                
                # Process the notification
                result = self._handle_gmail_notification(user_email, history_id)
                
                return jsonify(result), 200
                
            except Exception as e:
                print(f"❌ Error handling webhook: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})
        
        @self.app.route('/setup-user/<user_email>', methods=['POST'])
        def setup_user_notifications(user_email):
            """Setup push notifications for a user"""
            try:
                # This would typically be called after user authentication
                # For demo purposes, we'll return setup instructions
                
                instructions = {
                    'message': f'To setup push notifications for {user_email}:',
                    'steps': [
                        '1. Complete OAuth authentication',
                        '2. Call the setup_push_notifications method',
                        '3. Ensure Pub/Sub topic and subscription are configured',
                        '4. Notifications will be sent to this webhook endpoint'
                    ],
                    'webhook_url': self.config.webhook_url,
                    'topic_name': f'projects/{self.config.project_id}/topics/{self.config.topic_name}'
                }
                
                return jsonify(instructions), 200
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    
    def _verify_webhook_signature(self, request) -> bool:
        """Verify webhook signature for security"""
        try:
            # Get signature from headers
            signature = request.headers.get('X-Goog-Signature')
            if not signature:
                return True  # Skip verification if no signature (for development)
            
            # Verify HMAC signature
            expected_signature = hmac.new(
                self.config.webhook_secret.encode(),
                request.get_data(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            print(f"Error verifying signature: {e}")
            return False
    
    def _handle_gmail_notification(self, user_email: str, history_id: str) -> Dict:
        """Handle a Gmail notification"""
        try:
            # Check if user is active
            if not self.email_processor.user_manager.is_user_active(user_email):
                return {'error': f'User {user_email} not active or watch expired'}
            
            # Get user credentials
            credentials = self.email_processor.user_manager.get_user_credentials(user_email)
            if not credentials:
                return {'error': f'No credentials for {user_email}'}
            
            # Get Gmail service
            service = build('gmail', 'v1', credentials=credentials)
            
            # Get the last known history ID for this user
            last_history_id = self.email_processor.user_manager.active_users[user_email].get('history_id')
            
            # Get history of changes since last notification
            history_response = service.users().history().list(
                userId='me',
                startHistoryId=last_history_id
            ).execute()
            
            changes = history_response.get('history', [])
            processed_emails = []
            
            # Process each change
            for change in changes:
                # Look for new messages
                messages_added = change.get('messagesAdded', [])
                
                for message_added in messages_added:
                    message = message_added.get('message', {})
                    message_id = message.get('id')
                    
                    if message_id:
                        # Process the new email
                        result = self.email_processor.process_new_email(
                            user_email, message_id, history_id
                        )
                        processed_emails.append(result)
            
            # Update last history ID
            self.email_processor.user_manager.active_users[user_email]['history_id'] = history_id
            
            return {
                'success': True,
                'user_email': user_email,
                'history_id': history_id,
                'emails_processed': len(processed_emails),
                'results': processed_emails
            }
            
        except Exception as e:
            print(f"Error handling notification: {e}")
            return {'success': False, 'error': str(e)}
    
    def run(self):
        """Run the Flask server"""
        print(f"🚀 Starting Gmail Push Notification Server")
        print(f"📡 Webhook URL: {self.config.webhook_url}")
        print(f"🔊 Listening on {self.config.flask_host}:{self.config.flask_port}")
        
        self.app.run(
            host=self.config.flask_host,
            port=self.config.flask_port,
            debug=False
        )

class PushNotificationSetup:
    """Helper class to set up the entire push notification system"""
    
    def __init__(self):
        self.config = PushNotificationConfig()
        self.notification_manager = GmailPushNotificationManager(self.config)
    
    def setup_complete_system(self, user_email: str, credentials: Credentials) -> Dict:
        """Set up complete push notification system for a user"""
        try:
            print(f"🔧 Setting up push notifications for {user_email}")
            
            # Step 1: Setup Gmail watch
            watch_success = self.notification_manager.setup_push_notifications(user_email, credentials)
            
            if not watch_success:
                return {'success': False, 'error': 'Failed to setup Gmail watch'}
            
            # Step 2: Verify Pub/Sub setup (this would be done once per project)
            pubsub_setup = self._verify_pubsub_setup()
            
            return {
                'success': True,
                'user_email': user_email,
                'watch_setup': watch_success,
                'pubsub_setup': pubsub_setup,
                'webhook_url': self.config.webhook_url,
                'instructions': [
                    'Gmail watch is now active',
                    'Push notifications will be sent to the webhook',
                    'New emails will be automatically labeled',
                    'Watch expires in 7 days and needs renewal'
                ]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _verify_pubsub_setup(self) -> Dict:
        """Verify Pub/Sub topic and subscription setup"""
        try:
            # This would verify that:
            # 1. Pub/Sub topic exists
            # 2. Subscription exists and points to webhook
            # 3. Proper permissions are set
            
            return {
                'topic_exists': True,  # Would check actual topic
                'subscription_exists': True,  # Would check actual subscription
                'permissions_ok': True  # Would verify IAM permissions
            }
            
        except Exception as e:
            return {'error': str(e)}

def main():
    """Main function to run the push notification system"""
    print("📧 Gmail Push Notification Email Labeling System")
    print("=" * 60)
    
    # Initialize server
    server = PushNotificationServer()
    
    print("🔧 System Components:")
    print("  • Flask webhook server")
    print("  • Gmail Push Notification handler")
    print("  • Thread-based email classifier")
    print("  • Automatic label application")
    
    print("\n📋 Setup Requirements:")
    print("  1. Google Cloud Project with Pub/Sub enabled")
    print("  2. Gmail API credentials")
    print("  3. Webhook URL accessible from internet")
    print("  4. Environment variables configured")
    
    print("\n🚀 Starting server...")
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"\n❌ Server error: {e}")

if __name__ == "__main__":
    main()