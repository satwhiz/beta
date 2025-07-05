# simple_webhook_server.py - Simplified webhook server for testing
from flask import Flask, request, jsonify
import threading
import time
import json
from datetime import datetime
from typing import Dict, List
import os
from dotenv import load_dotenv

# Our imports
from agents.thread_email_classifier import ThreadEmailClassifier
from tools.gmail_tools import GmailTools
from utils.thread_organizer import ThreadOrganizer
from models.email_models import EmailMessage

class SimpleEmailMonitor:
    """Simple email monitoring without complex Pub/Sub setup"""
    
    def __init__(self):
        load_dotenv()
        self.classifier = ThreadEmailClassifier()
        self.thread_organizer = ThreadOrganizer()
        self.app = Flask(__name__)
        self.setup_routes()
        
        # Store last processed email IDs to avoid duplicates
        self.processed_emails = set()
        
        # User credentials storage (simplified)
        self.user_credentials = {}
    
    def setup_routes(self):
        """Setup Flask routes for webhook testing"""
        
        @self.app.route('/process-new-email', methods=['POST'])
        def process_new_email():
            """Manual endpoint to process a specific email"""
            try:
                data = request.get_json()
                user_email = data.get('user_email')
                message_id = data.get('message_id')
                
                if not user_email or not message_id:
                    return jsonify({
                        'error': 'user_email and message_id required'
                    }), 400
                
                # Process the email
                result = self._process_single_email(user_email, message_id)
                return jsonify(result)
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/start-monitoring/<user_email>', methods=['POST'])
        def start_monitoring(user_email):
            """Start monitoring emails for a user"""
            try:
                # This would start periodic checking for new emails
                success = self._setup_user_monitoring(user_email)
                
                if success:
                    return jsonify({
                        'message': f'Started monitoring emails for {user_email}',
                        'status': 'active',
                        'polling_interval': '30 seconds'
                    })
                else:
                    return jsonify({
                        'error': f'Failed to setup monitoring for {user_email}'
                    }), 500
                    
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'monitored_users': len(self.user_credentials),
                'processed_emails': len(self.processed_emails)
            })
        
        @self.app.route('/simulate-notification', methods=['POST'])
        def simulate_notification():
            """Simulate a Gmail push notification for testing"""
            try:
                data = request.get_json()
                user_email = data.get('user_email', 'gaurav@whizmail.ai')
                
                # Simulate checking for new emails
                result = self._check_for_new_emails(user_email)
                
                return jsonify({
                    'message': 'Simulated notification processed',
                    'user_email': user_email,
                    'result': result
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    
    def _setup_user_monitoring(self, user_email: str) -> bool:
        """Setup monitoring for a user (simplified OAuth)"""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            
            print(f"🔐 Setting up monitoring for {user_email}")
            
            # OAuth flow
            scopes = ['https://www.googleapis.com/auth/gmail.readonly',
                     'https://www.googleapis.com/auth/gmail.modify']
            
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes)
            credentials = flow.run_local_server(port=8081, access_type='offline')
            
            # Store credentials
            self.user_credentials[user_email] = credentials
            
            print(f"✅ Monitoring setup complete for {user_email}")
            
            # Start background monitoring
            self._start_background_monitoring(user_email)
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup monitoring: {e}")
            return False
    
    def _start_background_monitoring(self, user_email: str):
        """Start background thread to monitor emails"""
        def monitor_loop():
            print(f"🔄 Started background monitoring for {user_email}")
            
            while user_email in self.user_credentials:
                try:
                    self._check_for_new_emails(user_email)
                    time.sleep(30)  # Check every 30 seconds
                except Exception as e:
                    print(f"❌ Error in monitoring loop: {e}")
                    time.sleep(60)  # Wait longer on error
        
        # Start monitoring in background thread
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
    
    def _check_for_new_emails(self, user_email: str) -> Dict:
        """Check for new emails and process them"""
        try:
            if user_email not in self.user_credentials:
                return {'error': 'User not authenticated'}
            
            credentials = self.user_credentials[user_email]
            gmail_tools = GmailTools(credentials)
            
            # Get recent emails (last 5)
            recent_emails = gmail_tools.fetch_emails(limit=5)
            
            processed_count = 0
            results = []
            
            for email in recent_emails:
                # Skip if already processed
                if email.id in self.processed_emails:
                    continue
                
                # Process new email
                result = self._process_single_email(user_email, email.id)
                if result['success']:
                    processed_count += 1
                    results.append(result)
                    self.processed_emails.add(email.id)
            
            if processed_count > 0:
                print(f"📧 Processed {processed_count} new emails for {user_email}")
            
            return {
                'success': True,
                'user_email': user_email,
                'new_emails_processed': processed_count,
                'results': results
            }
            
        except Exception as e:
            print(f"❌ Error checking emails: {e}")
            return {'success': False, 'error': str(e)}
    
    def _process_single_email(self, user_email: str, message_id: str) -> Dict:
        """Process a single email and apply classification"""
        try:
            if user_email not in self.user_credentials:
                return {'success': False, 'error': 'User not authenticated'}
            
            credentials = self.user_credentials[user_email]
            gmail_tools = GmailTools(credentials)
            
            # Get the specific email
            from googleapiclient.discovery import build
            service = build('gmail', 'v1', credentials=credentials)
            
            message = service.users().messages().get(
                userId='me', 
                id=message_id, 
                format='full'
            ).execute()
            
            # Parse email
            email_obj = self._parse_gmail_message(message)
            if not email_obj:
                return {'success': False, 'error': 'Failed to parse email'}
            
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
                'reasoning': classification.reasoning[:100] + "...",
                'label_applied': label_success,
                'processed_at': datetime.now().isoformat()
            }
            
            print(f"✅ Processed: {email_obj.subject[:50]}... → {classification.label.value}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error processing email {message_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _parse_gmail_message(self, message_data: Dict) -> EmailMessage:
        """Parse Gmail message into EmailMessage object"""
        try:
            headers = message_data['payload']['headers']
            header_dict = {h['name']: h['value'] for h in headers}
            
            # Extract content
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
        import base64
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
            
            return content[:1000]  # Limit content length
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
    
    def run(self, port: int = 8080):
        """Run the Flask server"""
        print("🚀 Simple Email Monitoring Server")
        print("=" * 40)
        print(f"📡 Server running on http://localhost:{port}")
        print("\n🔗 Available endpoints:")
        print(f"  • POST /start-monitoring/<user_email> - Setup monitoring")
        print(f"  • POST /process-new-email - Process specific email")
        print(f"  • POST /simulate-notification - Test notification")
        print(f"  • GET /health - Health check")
        
        print("\n📧 How it works:")
        print("  1. Call /start-monitoring/<email> to setup user")
        print("  2. System polls Gmail every 30 seconds")
        print("  3. New emails are automatically classified")
        print("  4. Labels are applied to Gmail")
        
        self.app.run(host='0.0.0.0', port=port, debug=False)

def test_webhook_locally():
    """Test the webhook system locally"""
    print("🧪 Testing Webhook System Locally")
    print("=" * 40)
    
    # Initialize monitor
    monitor = SimpleEmailMonitor()
    
    print("✅ Email monitor initialized")
    print("🔄 Starting Flask server...")
    
    try:
        monitor.run(port=8080)
    except KeyboardInterrupt:
        print("\n👋 Server stopped")

if __name__ == "__main__":
    test_webhook_locally()