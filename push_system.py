# push_system.py - Complete Gmail Push Notification System
import os
import json
import base64
import hmac
import hashlib
from datetime import datetime
from typing import Dict, List, Optional
from flask import Flask, request, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Import our modules
from agents.thread_email_classifier import ThreadEmailClassifier
from tools.gmail_tools import GmailTools
from utils.thread_organizer import ThreadOrganizer
from models.email_models import EmailMessage

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
        
        # Flask settings
        self.flask_port = int(os.getenv("FLASK_PORT", "8080"))
        self.flask_host = os.getenv("FLASK_HOST", "0.0.0.0")

class GmailPushManager:
    """Manage Gmail Push Notifications"""
    
    def __init__(self, config: PushNotificationConfig):
        self.config = config
        self.active_watches = {}  # user_email -> watch_info
    
    def authenticate_user(self, user_email: str) -> Optional[Credentials]:
        """Authenticate a user for push notifications"""
        try:
            print(f"🔐 Authenticating {user_email} for push notifications...")
            
            scopes = [
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.modify'
            ]
            
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes)
            credentials = flow.run_local_server(port=0, access_type='offline')
            
            print(f"✅ Authentication successful for {user_email}")
            return credentials
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return None
    
    def setup_push_notifications(self, user_email: str, credentials: Credentials) -> Dict:
        """Setup Gmail push notifications for a user"""
        try:
            print(f"🔧 Setting up Gmail watch for {user_email}")
            
            # Create Gmail service
            service = build('gmail', 'v1', credentials=credentials)
            
            # Setup watch request
            watch_request = {
                'labelIds': ['INBOX'],  # Watch inbox for new emails
                'topicName': f'projects/{self.config.project_id}/topics/{self.config.topic_name}'
            }
            
            print(f"📡 Starting Gmail watch...")
            print(f"   Topic: projects/{self.config.project_id}/topics/{self.config.topic_name}")
            
            # Start watching
            watch_response = service.users().watch(userId='me', body=watch_request).execute()
            
            # Store watch info
            expiration_ms = int(watch_response.get('expiration', 0))
            expiration_dt = datetime.fromtimestamp(expiration_ms / 1000) if expiration_ms else None
            
            self.active_watches[user_email] = {
                'history_id': watch_response.get('historyId'),
                'expiration': expiration_dt,
                'credentials': credentials,
                'created_at': datetime.now()
            }
            
            print(f"✅ Gmail watch active for {user_email}")
            print(f"   History ID: {watch_response.get('historyId')}")
            print(f"   Expires: {expiration_dt}")
            print(f"🔔 Push notifications are now LIVE!")
            
            return {
                'success': True,
                'user_email': user_email,
                'history_id': watch_response.get('historyId'),
                'expiration': expiration_dt.isoformat() if expiration_dt else None
            }
            
        except Exception as e:
            print(f"❌ Failed to setup Gmail watch: {e}")
            return {'success': False, 'error': str(e)}

class EmailProcessor:
    """Process emails from push notifications"""
    
    def __init__(self):
        self.classifier = ThreadEmailClassifier()
        self.thread_organizer = ThreadOrganizer()
        print("✅ Email processor initialized")
    
    def process_notification(self, user_email: str, history_id: str, credentials: Credentials) -> Dict:
        """Process a Gmail push notification"""
        try:
            print(f"📧 Processing push notification for {user_email}")
            print(f"   History ID: {history_id}")
            
            # Create Gmail service
            service = build('gmail', 'v1', credentials=credentials)
            gmail_tools = GmailTools(credentials)
            
            # Get history changes since last notification
            print(f"🔍 Fetching history changes...")
            
            try:
                history_response = service.users().history().list(
                    userId='me',
                    startHistoryId=history_id
                ).execute()
            except Exception as e:
                if "Invalid historyId" in str(e):
                    print(f"⚠️ Invalid history ID, fetching recent emails instead")
                    # Fallback: get recent emails
                    recent_emails = gmail_tools.fetch_emails(limit=3)
                    if recent_emails:
                        return self._process_recent_emails(user_email, recent_emails[:1], gmail_tools)
                    else:
                        return {'success': False, 'error': 'No recent emails to process'}
                else:
                    raise
            
            changes = history_response.get('history', [])
            processed_emails = []
            
            print(f"📬 Found {len(changes)} history changes")
            
            # Process each change
            for change in changes:
                # Look for new messages
                messages_added = change.get('messagesAdded', [])
                
                for message_added in messages_added:
                    message = message_added.get('message', {})
                    message_id = message.get('id')
                    
                    if message_id:
                        print(f"🆕 Processing new message: {message_id}")
                        # Process the new email
                        result = self._process_single_email(
                            user_email, message_id, credentials, gmail_tools
                        )
                        processed_emails.append(result)
            
            return {
                'success': True,
                'user_email': user_email,
                'history_id': history_id,
                'emails_processed': len(processed_emails),
                'results': processed_emails
            }
            
        except Exception as e:
            print(f"❌ Error processing notification: {e}")
            return {'success': False, 'error': str(e)}
    
    def _process_recent_emails(self, user_email: str, emails: List[EmailMessage], gmail_tools: GmailTools) -> Dict:
        """Process recent emails as fallback"""
        processed_emails = []
        
        for email in emails:
            result = self._process_single_email(user_email, email.id, None, gmail_tools)
            processed_emails.append(result)
        
        return {
            'success': True,
            'user_email': user_email,
            'emails_processed': len(processed_emails),
            'results': processed_emails,
            'method': 'fallback_recent_emails'
        }
    
    def _process_single_email(self, user_email: str, message_id: str, 
                            credentials: Optional[Credentials], gmail_tools: GmailTools) -> Dict:
        """Process a single email"""
        try:
            # Get the email
            if credentials:
                service = build('gmail', 'v1', credentials=credentials)
                message = service.users().messages().get(
                    userId='me', 
                    id=message_id, 
                    format='full'
                ).execute()
                
                # Parse email
                email_obj = self._parse_gmail_message(message)
            else:
                # Use gmail_tools to get the email
                recent_emails = gmail_tools.fetch_emails(limit=10)
                email_obj = next((e for e in recent_emails if e.id == message_id), None)
            
            if not email_obj:
                return {'success': False, 'error': 'Failed to parse email'}
            
            print(f"📧 Processing: {email_obj.subject[:50]}...")
            
            # Get thread context
            thread_emails = gmail_tools.get_thread_messages(email_obj.thread_id)
            
            # Classify thread
            threads = {email_obj.thread_id: thread_emails}
            classifications = self.classifier.classify_multiple_threads(threads)
            
            if not classifications:
                return {'success': False, 'error': 'Classification failed'}
            
            classification = classifications[0]
            
            # Apply label
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
                'label_applied': label_success,
                'processed_at': datetime.now().isoformat()
            }
            
            print(f"⚡ INSTANT LABEL: {email_obj.subject[:40]}... → {classification.label.value}")
            return result
            
        except Exception as e:
            print(f"❌ Error processing email {message_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _parse_gmail_message(self, message_data: Dict) -> Optional[EmailMessage]:
        """Parse Gmail message into EmailMessage object"""
        try:
            headers = message_data['payload']['headers']
            header_dict = {h['name']: h['value'] for h in headers}
            
            # Extract content (simplified for push notifications)
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
        """Extract content from email payload"""
        try:
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                        data = part['body']['data']
                        return base64.urlsafe_b64decode(data).decode('utf-8')[:1000]
            elif payload['mimeType'] == 'text/plain' and 'data' in payload['body']:
                data = payload['body']['data']
                return base64.urlsafe_b64decode(data).decode('utf-8')[:1000]
            return ""
        except:
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
        self.push_manager = GmailPushManager(self.config)
        self.email_processor = EmailProcessor()
        self.setup_routes()
        
        print("🚀 Push Notification Server initialized")
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/gmail-webhook', methods=['POST'])
        def gmail_webhook():
            """Handle Gmail push notifications"""
            try:
                print(f"📩 Received push notification!")
                
                # Parse Pub/Sub message
                envelope = request.get_json()
                if not envelope:
                    print("❌ No JSON body in request")
                    return jsonify({'error': 'No JSON body'}), 400
                
                pubsub_message = envelope.get('message')
                if not pubsub_message:
                    print("❌ No message in envelope")
                    return jsonify({'error': 'No message in envelope'}), 400
                
                # Decode message data
                message_data = base64.b64decode(pubsub_message['data']).decode('utf-8')
                notification_data = json.loads(message_data)
                
                # Extract notification details
                user_email = notification_data.get('emailAddress')
                history_id = notification_data.get('historyId')
                
                print(f"📧 Notification for: {user_email}")
                print(f"📊 History ID: {history_id}")
                
                if not user_email or not history_id:
                    return jsonify({'error': 'Missing email or history ID'}), 400
                
                # Get user credentials
                if user_email not in self.push_manager.active_watches:
                    return jsonify({'error': f'No active watch for {user_email}'}), 400
                
                credentials = self.push_manager.active_watches[user_email]['credentials']
                
                # Process the notification
                result = self.email_processor.process_notification(
                    user_email, history_id, credentials
                )
                
                return jsonify(result), 200
                
            except Exception as e:
                print(f"❌ Error handling webhook: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/setup/<user_email>', methods=['POST'])
        def setup_user_push(user_email):
            """Setup push notifications for a user"""
            try:
                print(f"🔧 Setting up push notifications for {user_email}")
                
                # Authenticate user
                credentials = self.push_manager.authenticate_user(user_email)
                if not credentials:
                    return jsonify({'error': 'Authentication failed'}), 400
                
                # Setup push notifications
                result = self.push_manager.setup_push_notifications(user_email, credentials)
                
                return jsonify(result), 200
                
            except Exception as e:
                print(f"❌ Setup error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'active_watches': len(self.push_manager.active_watches),
                'webhook_url': self.config.webhook_url,
                'project_id': self.config.project_id
            })
        
        @self.app.route('/', methods=['GET'])
        def home():
            """Home page with status"""
            status = {
                'service': 'Gmail Push Notification System',
                'status': 'running',
                'active_watches': len(self.push_manager.active_watches),
                'endpoints': {
                    'webhook': '/gmail-webhook',
                    'setup': '/setup/<user_email>',
                    'health': '/health'
                }
            }
            return jsonify(status)
    
    def run(self):
        """Run the Flask server"""
        print(f"🚀 Gmail Push Notification Server Starting...")
        print(f"📡 Webhook URL: {self.config.webhook_url}")
        print(f"🔊 Listening on {self.config.flask_host}:{self.config.flask_port}")
        print(f"🔔 Project: {self.config.project_id}")
        print(f"📬 Topic: {self.config.topic_name}")
        print(f"🌊 Ready for INSTANT email processing!")
        print(f"")
        print(f"🎯 To setup a user: POST /setup/<user_email>")
        print(f"💡 Test health: GET /health")
        
        self.app.run(
            host=self.config.flask_host,
            port=self.config.flask_port,
            debug=False
        )

def main():
    """Main function"""
    print("📧 Gmail Push Notification System")
    print("=" * 40)
    
    # Check basic requirements
    load_dotenv()
    
    if not os.getenv("WEBHOOK_URL") or "your-domain" in os.getenv("WEBHOOK_URL"):
        print("❌ WEBHOOK_URL not properly configured in .env")
        print("🔧 Please update .env with your ngrok URL")
        return
    
    if not os.path.exists("credentials.json"):
        print("❌ credentials.json not found")
        print("📥 Please download from Google Cloud Console")
        return
    
    # Start server
    server = PushNotificationServer()
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("\n👋 Push notification server stopped")

if __name__ == "__main__":
    main()