# push_notifications/monitoring/email_monitor.py
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from agents.thread_email_classifier import ThreadEmailClassifier
from tools.gmail_tools import GmailTools
from models.email_models import EmailMessage

class EmailMonitor:
    """Monitor Gmail for new emails and process them automatically"""
    
    def __init__(self):
        self.classifier = ThreadEmailClassifier()
        self.active_monitors = {}  # user_email -> monitor_info
        self.processed_emails: Set[str] = set()
        self.is_running = False
        
    def start_monitoring(self, user_email: str, credentials: Credentials, 
                        check_interval: int = 30) -> bool:
        """Start monitoring emails for a user"""
        try:
            if user_email in self.active_monitors:
                print(f"⚠️  Already monitoring {user_email}")
                return True
            
            # Test Gmail connection
            gmail_tools = GmailTools(credentials)
            service = build('gmail', 'v1', credentials=credentials)
            
            # Get initial email count to establish baseline
            profile = service.users().getProfile(userId='me').execute()
            
            monitor_info = {
                'user_email': user_email,
                'credentials': credentials,
                'gmail_tools': gmail_tools,
                'service': service,
                'check_interval': check_interval,
                'last_check': datetime.now(),
                'total_messages': profile.get('messagesTotal', 0),
                'emails_processed': 0,
                'thread': None,
                'is_active': True
            }
            
            self.active_monitors[user_email] = monitor_info
            
            # Start monitoring thread
            monitor_thread = threading.Thread(
                target=self._monitor_user_emails,
                args=(user_email,),
                daemon=True
            )
            monitor_thread.start()
            monitor_info['thread'] = monitor_thread
            
            print(f"✅ Started monitoring {user_email} (check every {check_interval}s)")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start monitoring {user_email}: {e}")
            return False
    
    def stop_monitoring(self, user_email: str) -> bool:
        """Stop monitoring emails for a user"""
        try:
            if user_email not in self.active_monitors:
                print(f"⚠️  Not monitoring {user_email}")
                return True
            
            # Mark as inactive
            self.active_monitors[user_email]['is_active'] = False
            
            # Remove from active monitors
            del self.active_monitors[user_email]
            
            print(f"🛑 Stopped monitoring {user_email}")
            return True
            
        except Exception as e:
            print(f"❌ Error stopping monitoring: {e}")
            return False
    
    def get_monitoring_status(self) -> Dict:
        """Get status of all active monitors"""
        status = {
            'total_monitors': len(self.active_monitors),
            'processed_emails': len(self.processed_emails),
            'monitors': []
        }
        
        for user_email, info in self.active_monitors.items():
            monitor_status = {
                'user_email': user_email,
                'is_active': info['is_active'],
                'last_check': info['last_check'].isoformat(),
                'emails_processed': info['emails_processed'],
                'check_interval': info['check_interval']
            }
            status['monitors'].append(monitor_status)
        
        return status
    
    def _monitor_user_emails(self, user_email: str):
        """Background monitoring loop for a user"""
        print(f"🔄 Starting monitoring loop for {user_email}")
        
        monitor_info = self.active_monitors[user_email]
        
        while monitor_info['is_active']:
            try:
                # Check for new emails
                new_emails = self._check_for_new_emails(user_email)
                
                if new_emails:
                    print(f"📧 Found {len(new_emails)} new emails for {user_email}")
                    
                    # Process each new email
                    for email in new_emails:
                        if email.id not in self.processed_emails:
                            result = self._process_new_email(user_email, email)
                            if result['success']:
                                self.processed_emails.add(email.id)
                                monitor_info['emails_processed'] += 1
                                
                                print(f"✅ Processed: {email.subject[:40]}... → {result['label']}")
                
                # Update last check time
                monitor_info['last_check'] = datetime.now()
                
                # Wait before next check
                time.sleep(monitor_info['check_interval'])
                
            except Exception as e:
                print(f"❌ Error in monitoring loop for {user_email}: {e}")
                time.sleep(60)  # Wait longer on error
        
        print(f"🛑 Monitoring loop ended for {user_email}")
    
    def _check_for_new_emails(self, user_email: str) -> List[EmailMessage]:
        """Check for new emails since last check"""
        try:
            monitor_info = self.active_monitors[user_email]
            gmail_tools = monitor_info['gmail_tools']
            
            # Get recent emails (last 10)
            recent_emails = gmail_tools.fetch_emails(limit=10)
            
            # Filter for emails newer than last check
            last_check = monitor_info['last_check']
            new_emails = []
            
            for email in recent_emails:
                if email.date > last_check and email.id not in self.processed_emails:
                    new_emails.append(email)
            
            return new_emails
            
        except Exception as e:
            print(f"❌ Error checking for new emails: {e}")
            return []
    
    def _process_new_email(self, user_email: str, email: EmailMessage) -> Dict:
        """Process a single new email"""
        try:
            monitor_info = self.active_monitors[user_email]
            gmail_tools = monitor_info['gmail_tools']
            
            # Get thread context
            thread_emails = gmail_tools.get_thread_messages(email.thread_id)
            
            # Classify thread
            threads = {email.thread_id: thread_emails}
            classifications = self.classifier.classify_multiple_threads(threads)
            
            if not classifications:
                return {'success': False, 'error': 'Classification failed'}
            
            classification = classifications[0]
            
            # Apply label
            label_success = gmail_tools.apply_label(email.id, classification.label.value)
            
            return {
                'success': True,
                'user_email': user_email,
                'email_id': email.id,
                'thread_id': email.thread_id,
                'subject': email.subject,
                'from_email': email.from_email,
                'label': classification.label.value,
                'confidence': classification.confidence,
                'label_applied': label_success,
                'processed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error processing email: {e}")
            return {'success': False, 'error': str(e)}