# main.py - Updated for thread-based classification
import os
import json
import csv
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dotenv import load_dotenv

# Google API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
import email

# Our imports
from agents.thread_email_classifier import ThreadEmailClassifier
from models.email_models import EmailMessage
from models.response_models import ThreadProcessingResponse, ThreadInfo
from utils.thread_organizer import ThreadOrganizer

class UserManager:
    def __init__(self, csv_file: str = "users.csv"):
        self.csv_file = csv_file
        self._ensure_csv_exists()
    
    def _ensure_csv_exists(self):
        """Create CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    'user_email', 'access_token_hash', 'refresh_token_hash', 
                    'created_at', 'last_processed_at', 'total_threads_processed', 'total_emails_processed'
                ])
            print(f"Created user database: {self.csv_file}")
    
    def user_exists(self, email: str) -> bool:
        """Check if user exists in database"""
        try:
            with open(self.csv_file, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row['user_email'] == email:
                        return True
            return False
        except Exception as e:
            print(f"Error checking user existence: {e}")
            return False
    
    def add_user(self, email: str, access_token: str, refresh_token: str) -> bool:
        """Add new user to database"""
        try:
            # Hash tokens for security
            access_hash = hashlib.sha256(access_token.encode()).hexdigest()[:16]
            refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()[:16]
            
            with open(self.csv_file, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    email, access_hash, refresh_hash,
                    datetime.now().isoformat(), '', 0, 0
                ])
            
            print(f"Added user: {email}")
            return True
        except Exception as e:
            print(f"Error adding user: {e}")
            return False
    
    def update_processing_stats(self, email: str, threads_processed: int, emails_processed: int):
        """Update user's processing statistics"""
        try:
            # Read all rows
            rows = []
            with open(self.csv_file, 'r') as file:
                reader = csv.DictReader(file)
                rows = list(reader)
            
            # Update the specific user
            for row in rows:
                if row['user_email'] == email:
                    row['last_processed_at'] = datetime.now().isoformat()
                    row['total_threads_processed'] = str(int(row.get('total_threads_processed', 0)) + threads_processed)
                    row['total_emails_processed'] = str(int(row.get('total_emails_processed', 0)) + emails_processed)
                    break
            
            # Write back
            with open(self.csv_file, 'w', newline='') as file:
                fieldnames = ['user_email', 'access_token_hash', 'refresh_token_hash', 
                             'created_at', 'last_processed_at', 'total_threads_processed', 'total_emails_processed']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            
            print(f"Updated stats for {email}: +{threads_processed} threads, +{emails_processed} emails")
        except Exception as e:
            print(f"Error updating stats: {e}")

class GmailConnector:
    def __init__(self, credentials_file: str = "credentials.json"):
        self.credentials_file = credentials_file
        self.scopes = ['https://www.googleapis.com/auth/gmail.readonly']
    
    def authenticate_user(self, user_email: str) -> Optional[Dict[str, str]]:
        """Authenticate user and return tokens"""
        try:
            print(f"Starting OAuth flow for {user_email}...")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_file, self.scopes
            )
            
            print(f"\n🔐 Starting authentication for {user_email}")
            print("This will open a browser window for Google sign-in...")
            print("Please make sure to sign in with the correct account!")
            
            input("Press Enter to continue...")
            
            # Use the EXACT same method as test_oauth.py that worked
            credentials = flow.run_local_server(
                port=8080,
                access_type='offline'
            )
            
            print("✅ Authentication successful!")
            
            return {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret
            }
            
        except Exception as e:
            print(f"Authentication failed: {e}")
            return None
    
    def get_gmail_service(self, tokens: Dict[str, str]):
        """Create Gmail service from tokens"""
        try:
            credentials = Credentials(
                token=tokens['access_token'],
                refresh_token=tokens['refresh_token'],
                token_uri=tokens['token_uri'],
                client_id=tokens['client_id'],
                client_secret=tokens['client_secret']
            )
            
            # Refresh if needed
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            
            return build('gmail', 'v1', credentials=credentials)
            
        except Exception as e:
            print(f"Error creating Gmail service: {e}")
            return None
    
    def fetch_recent_emails(self, service, limit: int = 50) -> List[EmailMessage]:
        """Fetch recent emails from Gmail"""
        try:
            print(f"Fetching last {limit} emails...")
            
            # Get message list
            results = service.users().messages().list(
                userId='me',
                maxResults=limit
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            print(f"Processing {len(messages)} emails...")
            
            for i, message in enumerate(messages):
                try:
                    # Get full message
                    msg = service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='full'
                    ).execute()
                    
                    # Parse email
                    email_obj = self._parse_email(msg)
                    if email_obj:
                        emails.append(email_obj)
                    
                    # Progress indicator
                    if (i + 1) % 10 == 0:
                        print(f"Processed {i + 1}/{len(messages)} emails")
                        
                except Exception as e:
                    print(f"Error processing email {message['id']}: {e}")
                    continue
            
            print(f"Successfully fetched {len(emails)} emails")
            return emails
            
        except Exception as e:
            print(f"Error fetching emails: {e}")
            return []
    
    def _parse_email(self, message_data: Dict) -> Optional[EmailMessage]:
        """Parse Gmail message into EmailMessage object"""
        try:
            headers = message_data['payload']['headers']
            header_dict = {h['name']: h['value'] for h in headers}
            
            # Extract content
            content = self._extract_content(message_data['payload'])
            
            # Parse date
            date_str = header_dict.get('Date', '')
            try:
                # Try to parse the date
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
            print(f"Error parsing email: {e}")
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
        
        # Simple email extraction
        import re
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', email_string)
        return emails

class ThreadBasedEmailSystem:
    def __init__(self):
        load_dotenv()
        
        self.user_manager = UserManager()
        self.gmail_connector = GmailConnector()
        self.thread_classifier = ThreadEmailClassifier()
        self.thread_organizer = ThreadOrganizer()
        
        print("Thread-Based Email System initialized")
    
    def process_user(self, user_email: str, email_limit: int = 50, force_reprocess: bool = False) -> Dict:
        """
        Main function to process a user's emails by threads
        
        Args:
            user_email: User's email address
            email_limit: Number of recent emails to process
            
        Returns:
            Dict with processing results
        """
        result = {
            'user_email': user_email,
            'success': False,
            'is_new_user': False,
            'emails_processed': 0,
            'threads_processed': 0,
            'thread_classifications': [],
            'thread_statistics': {},
            'error': None
        }
        
        try:
            print(f"\n{'='*60}")
            print(f"Processing user: {user_email}")
            print(f"{'='*60}")
            
            # Check if user exists
            user_exists = self.user_manager.user_exists(user_email)
            result['is_new_user'] = not user_exists
            
            if user_exists and not force_reprocess:
                print(f"✅ User {user_email} already exists in database")
                print("ℹ️  Skipping email processing (user already processed)")
                print("💡 Use force_reprocess=True to reprocess existing user")
                result['success'] = True
                return result
            
            if not user_exists:
                print(f"🆕 New user detected: {user_email}")
                print("🔐 Starting authentication process...")
                
                # Authenticate user
                tokens = self.gmail_connector.authenticate_user(user_email)
                if not tokens:
                    result['error'] = "Authentication failed"
                    return result
                
                print("✅ Authentication successful")
                
                # Add user to database
                if not self.user_manager.add_user(user_email, tokens['access_token'], tokens['refresh_token']):
                    result['error'] = "Failed to add user to database"
                    return result
                
                print("✅ User added to database")
            else:
                print(f"🔄 Force reprocessing existing user: {user_email}")
                # For existing users, we'll use stored tokens (simplified for demo)
                # In production, you'd retrieve and refresh the stored tokens
                print("⚠️  Using demo mode - will need fresh authentication")
                tokens = self.gmail_connector.authenticate_user(user_email)
                if not tokens:
                    result['error'] = "Re-authentication failed"
                    return result
                print("✅ Re-authentication successful")
            
            # Get Gmail service
            gmail_service = self.gmail_connector.get_gmail_service(tokens)
            if not gmail_service:
                result['error'] = "Failed to create Gmail service"
                return result
            
            print("✅ Gmail service created")
            
            # Fetch emails
            emails = self.gmail_connector.fetch_recent_emails(gmail_service, email_limit)
            if not emails:
                result['error'] = "No emails fetched"
                return result
            
            print(f"✅ Fetched {len(emails)} emails")
            
            # Organize emails by threads
            print("🧵 Organizing emails by threads...")
            threads = self.thread_organizer.organize_emails_by_thread(emails)
            thread_info = self.thread_organizer.get_thread_info(threads)
            thread_stats = self.thread_organizer.get_thread_statistics(threads)
            
            print(f"✅ Organized into {len(threads)} threads")
            print(f"   📊 Thread Statistics:")
            print(f"   • Single email threads: {thread_stats['single_email_threads']}")
            print(f"   • Multi-email threads: {thread_stats['multi_email_threads']}")
            print(f"   • Longest thread: {thread_stats['longest_thread']} emails")
            print(f"   • Average emails per thread: {thread_stats['avg_emails_per_thread']}")
            
            # Classify threads
            print("🏷️  Starting thread-based classification...")
            classifications = self.thread_classifier.classify_multiple_threads(threads)
            
            print(f"✅ Classified {len(classifications)} threads")
            
            # Prepare detailed results
            classification_results = []
            for classification in classifications:
                thread_emails = threads[classification.thread_id]
                thread_details = next((t for t in thread_info if t.thread_id == classification.thread_id), None)
                
                result_item = {
                    'thread_id': classification.thread_id,
                    'label': classification.label.value,
                    'confidence': classification.confidence,
                    'reasoning': classification.reasoning,
                    'email_count': classification.email_count,
                    'subject': thread_details.subject if thread_details else 'Unknown',
                    'participants': thread_details.participants if thread_details else [],
                    'start_date': thread_details.start_date if thread_details else '',
                    'last_activity': thread_details.last_activity if thread_details else ''
                }
                
                classification_results.append(result_item)
            
            # Update user stats
            self.user_manager.update_processing_stats(user_email, len(threads), len(emails))
            
            # Prepare final results
            result.update({
                'success': True,
                'emails_processed': len(emails),
                'threads_processed': len(threads),
                'thread_classifications': classification_results,
                'thread_statistics': thread_stats
            })
            
            # Print summary
            self._print_summary(classification_results, thread_stats)
            
            return result
            
        except Exception as e:
            print(f"❌ Error processing user: {e}")
            result['error'] = str(e)
            return result
    
    def _print_summary(self, classifications: List[Dict], thread_stats: Dict):
        """Print detailed classification summary"""
        print(f"\n{'='*60}")
        print("📊 THREAD CLASSIFICATION SUMMARY")
        print(f"{'='*60}")
        
        # Count labels
        label_counts = {}
        total_confidence = 0
        for classification in classifications:
            label = classification['label']
            label_counts[label] = label_counts.get(label, 0) + 1
            total_confidence += classification['confidence']
        
        total_threads = len(classifications)
        avg_confidence = total_confidence / total_threads if total_threads > 0 else 0
        
        print(f"📈 Overall Statistics:")
        print(f"   • Total threads processed: {total_threads}")
        print(f"   • Total emails processed: {thread_stats['total_emails']}")
        print(f"   • Average confidence: {avg_confidence:.2f}")
        print(f"   • Average emails per thread: {thread_stats['avg_emails_per_thread']}")
        
        print(f"\n🏷️  Label Distribution:")
        for label, count in sorted(label_counts.items()):
            percentage = (count / total_threads * 100) if total_threads > 0 else 0
            print(f"   {label.upper():15}: {count:3} threads ({percentage:5.1f}%)")
        
        print(f"\n📧 Thread Size Distribution:")
        for size_range, count in thread_stats['thread_size_distribution'].items():
            percentage = (count / total_threads * 100) if total_threads > 0 else 0
            print(f"   {size_range:15}: {count:3} threads ({percentage:5.1f}%)")
        
        # Show detailed examples
        print(f"\n🔍 SAMPLE THREAD CLASSIFICATIONS:")
        for i, classification in enumerate(classifications[:5]):  # Show first 5
            print(f"\n{i+1}. Thread: {classification['subject'][:60]}...")
            print(f"   📧 Emails: {classification['email_count']}")
            print(f"   👥 Participants: {len(classification['participants'])}")
            print(f"   🏷️  Label: {classification['label'].upper()} (confidence: {classification['confidence']:.2f})")
            print(f"   💭 Reasoning: {classification['reasoning'][:150]}...")
            if classification['participants']:
                print(f"   👥 Participants: {', '.join(classification['participants'][:3])}{'...' if len(classification['participants']) > 3 else ''}")

def main():
    """Main function for thread-based email processing"""
    try:
        # Initialize system
        thread_system = ThreadBasedEmailSystem()
        
        # Test user
        test_user = "gaurav@whizmail.ai"
        
        # Check if user exists
        user_exists = thread_system.user_manager.user_exists(test_user)
        
        print("🧵 Thread-Based Email Classification System")
        print("=" * 50)
        print(f"Test user: {test_user}")
        print("This system will:")
        print("1. Check if user exists in database")
        print("2. If new user, authenticate with Google")
        print("3. Fetch last 50 emails")
        print("4. Organize emails into conversation threads")
        print("5. Classify each THREAD (not individual emails)")
        print("6. Show thread-based analysis and results")
        
        # Ask for confirmation
        if user_exists:
            print(f"\n⚠️  User {test_user} already exists!")
            print("Options:")
            print("1. Skip processing (recommended)")
            print("2. Force reprocess (for testing)")
            choice = input("Enter choice (1 or 2): ").strip()
            if choice == "1":
                print("Skipped processing")
                return
            elif choice == "2":
                force_reprocess = True
                print("Will force reprocess...")
            else:
                print("Invalid choice, cancelling")
                return
        else:
            confirm = input(f"\nProceed with processing {test_user}? (y/n): ").lower()
            if confirm != 'y':
                print("Cancelled")
                return
            force_reprocess = False
        
        # Process user
        result = thread_system.process_user(test_user, email_limit=50, force_reprocess=force_reprocess)
        
        # Final results
        print(f"\n{'='*60}")
        print("🏁 FINAL RESULTS")
        print(f"{'='*60}")
        print(f"User: {result['user_email']}")
        print(f"Success: {result['success']}")
        print(f"New User: {result['is_new_user']}")
        print(f"Emails Processed: {result['emails_processed']}")
        print(f"Threads Processed: {result['threads_processed']}")
        
        if result['error']:
            print(f"Error: {result['error']}")
        
        if result['success']:
            print("✅ Thread-based processing completed successfully!")
            print("📊 Check users.csv for user database")
            print("🧵 Each thread has been classified as a conversation unit")
        
    except Exception as e:
        print(f"❌ System error: {e}")

if __name__ == "__main__":
    main()# main.py - Backend-ready email labeling system
import os
import json
import csv
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dotenv import load_dotenv

# Google API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
import email

# Our imports
from agents.email_classifier import EmailClassifierAgent
from models.email_models import EmailMessage

class UserManager:
    def __init__(self, csv_file: str = "users.csv"):
        self.csv_file = csv_file
        self._ensure_csv_exists()
    
    def _ensure_csv_exists(self):
        """Create CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    'user_email', 'access_token_hash', 'refresh_token_hash', 
                    'created_at', 'last_processed_at', 'total_emails_processed'
                ])
            print(f"Created user database: {self.csv_file}")
    
    def user_exists(self, email: str) -> bool:
        """Check if user exists in database"""
        try:
            with open(self.csv_file, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row['user_email'] == email:
                        return True
            return False
        except Exception as e:
            print(f"Error checking user existence: {e}")
            return False
    
    def add_user(self, email: str, access_token: str, refresh_token: str) -> bool:
        """Add new user to database"""
        try:
            # Hash tokens for security
            access_hash = hashlib.sha256(access_token.encode()).hexdigest()[:16]
            refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()[:16]
            
            with open(self.csv_file, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    email, access_hash, refresh_hash,
                    datetime.now().isoformat(), '', 0
                ])
            
            print(f"Added user: {email}")
            return True
        except Exception as e:
            print(f"Error adding user: {e}")
            return False
    
    def update_processing_stats(self, email: str, emails_processed: int):
        """Update user's processing statistics"""
        try:
            # Read all rows
            rows = []
            with open(self.csv_file, 'r') as file:
                reader = csv.DictReader(file)
                rows = list(reader)
            
            # Update the specific user
            for row in rows:
                if row['user_email'] == email:
                    row['last_processed_at'] = datetime.now().isoformat()
                    row['total_emails_processed'] = str(int(row['total_emails_processed']) + emails_processed)
                    break
            
            # Write back
            with open(self.csv_file, 'w', newline='') as file:
                fieldnames = ['user_email', 'access_token_hash', 'refresh_token_hash', 
                             'created_at', 'last_processed_at', 'total_emails_processed']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            
            print(f"Updated stats for {email}: +{emails_processed} emails")
        except Exception as e:
            print(f"Error updating stats: {e}")

class GmailConnector:
    def __init__(self, credentials_file: str = "credentials.json"):
        self.credentials_file = credentials_file
        self.scopes = ['https://www.googleapis.com/auth/gmail.readonly']
    
    def authenticate_user(self, user_email: str) -> Optional[Dict[str, str]]:
        """Authenticate user and return tokens"""
        try:
            print(f"Starting OAuth flow for {user_email}...")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_file, self.scopes
            )
            
            print(f"\n🔐 Starting authentication for {user_email}")
            print("This will open a browser window for Google sign-in...")
            print("Please make sure to sign in with the correct account!")
            
            input("Press Enter to continue...")
            
            # Use the EXACT same method as test_oauth.py that worked
            credentials = flow.run_local_server(
                port=8080,
                access_type='offline'
            )
            
            print("✅ Authentication successful!")
            
            return {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret
            }
            
        except Exception as e:
            print(f"Authentication failed: {e}")
            return None
    
    def get_gmail_service(self, tokens: Dict[str, str]):
        """Create Gmail service from tokens"""
        try:
            credentials = Credentials(
                token=tokens['access_token'],
                refresh_token=tokens['refresh_token'],
                token_uri=tokens['token_uri'],
                client_id=tokens['client_id'],
                client_secret=tokens['client_secret']
            )
            
            # Refresh if needed
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            
            return build('gmail', 'v1', credentials=credentials)
            
        except Exception as e:
            print(f"Error creating Gmail service: {e}")
            return None
    
    def fetch_recent_emails(self, service, limit: int = 50) -> List[EmailMessage]:
        """Fetch recent emails from Gmail"""
        try:
            print(f"Fetching last {limit} emails...")
            
            # Get message list
            results = service.users().messages().list(
                userId='me',
                maxResults=limit
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            print(f"Processing {len(messages)} emails...")
            
            for i, message in enumerate(messages):
                try:
                    # Get full message
                    msg = service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='full'
                    ).execute()
                    
                    # Parse email
                    email_obj = self._parse_email(msg)
                    if email_obj:
                        emails.append(email_obj)
                    
                    # Progress indicator
                    if (i + 1) % 10 == 0:
                        print(f"Processed {i + 1}/{len(messages)} emails")
                        
                except Exception as e:
                    print(f"Error processing email {message['id']}: {e}")
                    continue
            
            print(f"Successfully fetched {len(emails)} emails")
            return emails
            
        except Exception as e:
            print(f"Error fetching emails: {e}")
            return []
    
    def _parse_email(self, message_data: Dict) -> Optional[EmailMessage]:
        """Parse Gmail message into EmailMessage object"""
        try:
            headers = message_data['payload']['headers']
            header_dict = {h['name']: h['value'] for h in headers}
            
            # Extract content
            content = self._extract_content(message_data['payload'])
            
            # Parse date
            date_str = header_dict.get('Date', '')
            try:
                # Try to parse the date
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
            print(f"Error parsing email: {e}")
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
        
        # Simple email extraction
        import re
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', email_string)
        return emails

class BackendEmailSystem:
    def __init__(self):
        load_dotenv()
        
        self.user_manager = UserManager()
        self.gmail_connector = GmailConnector()
        self.email_classifier = EmailClassifierAgent()
        
        print("Backend Email System initialized")
    
    def process_user(self, user_email: str, email_limit: int = 50) -> Dict:
        """
        Main function to process a user's emails
        
        Args:
            user_email: User's email address
            email_limit: Number of recent emails to process
            
        Returns:
            Dict with processing results
        """
        result = {
            'user_email': user_email,
            'success': False,
            'is_new_user': False,
            'emails_processed': 0,
            'classifications': [],
            'error': None
        }
        
        try:
            print(f"\n{'='*60}")
            print(f"Processing user: {user_email}")
            print(f"{'='*60}")
            
            # Check if user exists
            user_exists = self.user_manager.user_exists(user_email)
            result['is_new_user'] = not user_exists
            
            if user_exists:
                print(f"✅ User {user_email} already exists in database")
                print("ℹ️  Skipping email processing (user already processed)")
                result['success'] = True
                return result
            
            print(f"🆕 New user detected: {user_email}")
            print("🔐 Starting authentication process...")
            
            # Authenticate user
            tokens = self.gmail_connector.authenticate_user(user_email)
            if not tokens:
                result['error'] = "Authentication failed"
                return result
            
            print("✅ Authentication successful")
            
            # Add user to database
            if not self.user_manager.add_user(user_email, tokens['access_token'], tokens['refresh_token']):
                result['error'] = "Failed to add user to database"
                return result
            
            print("✅ User added to database")
            
            # Get Gmail service
            gmail_service = self.gmail_connector.get_gmail_service(tokens)
            if not gmail_service:
                result['error'] = "Failed to create Gmail service"
                return result
            
            print("✅ Gmail service created")
            
            # Fetch emails
            emails = self.gmail_connector.fetch_recent_emails(gmail_service, email_limit)
            if not emails:
                result['error'] = "No emails fetched"
                return result
            
            print(f"✅ Fetched {len(emails)} emails")
            
            # Classify emails
            print("🏷️  Starting email classification...")
            classifications = []
            
            for i, email in enumerate(emails):
                try:
                    classification = self.email_classifier.classify_email(email)
                    
                    classification_result = {
                        'email_id': email.id,
                        'subject': email.subject[:50] + "..." if len(email.subject) > 50 else email.subject,
                        'from_email': email.from_email,
                        'label': classification.label.value,
                        'confidence': classification.confidence,
                        'reasoning': classification.reasoning
                    }
                    
                    classifications.append(classification_result)
                    
                    # Progress indicator
                    if (i + 1) % 10 == 0:
                        print(f"Classified {i + 1}/{len(emails)} emails")
                        
                except Exception as e:
                    print(f"Error classifying email {email.id}: {e}")
                    continue
            
            print(f"✅ Classified {len(classifications)} emails")
            
            # Update user stats
            self.user_manager.update_processing_stats(user_email, len(classifications))
            
            # Prepare results
            result.update({
                'success': True,
                'emails_processed': len(classifications),
                'classifications': classifications
            })
            
            # Print summary
            self._print_summary(classifications)
            
            return result
            
        except Exception as e:
            print(f"❌ Error processing user: {e}")
            result['error'] = str(e)
            return result
    
    def _print_summary(self, classifications: List[Dict]):
        """Print classification summary"""
        print(f"\n{'='*60}")
        print("📊 CLASSIFICATION SUMMARY")
        print(f"{'='*60}")
        
        # Count labels
        label_counts = {}
        for classification in classifications:
            label = classification['label']
            label_counts[label] = label_counts.get(label, 0) + 1
        
        total = len(classifications)
        for label, count in sorted(label_counts.items()):
            percentage = (count / total * 100) if total > 0 else 0
            print(f"{label.upper():15}: {count:3} emails ({percentage:5.1f}%)")
        
        print(f"{'TOTAL':15}: {total:3} emails")
        
        # Show some examples
        print(f"\n📧 SAMPLE CLASSIFICATIONS:")
        for classification in classifications[:3]:
            print(f"\n• Subject: {classification['subject']}")
            print(f"  Label: {classification['label'].upper()} (confidence: {classification['confidence']:.2f})")
            print(f"  Reasoning: {classification['reasoning'][:100]}...")

def main():
    """Main function for backend usage"""
    try:
        # Initialize system
        backend_system = BackendEmailSystem()
        
        # Test user
        test_user = "gaurav@whizmail.ai"
        
        print("🚀 Backend Email Labeling System")
        print("=" * 50)
        print(f"Test user: {test_user}")
        print("This system will:")
        print("1. Check if user exists in database")
        print("2. If new user, authenticate with Google")
        print("3. Fetch last 50 emails")
        print("4. Classify all emails")
        print("5. Store results")
        
        # Ask for confirmation
        confirm = input(f"\nProceed with processing {test_user}? (y/n): ").lower()
        if confirm != 'y':
            print("Cancelled")
            return
        
        # Process user
        result = backend_system.process_user(test_user, email_limit=50)
        
        # Final results
        print(f"\n{'='*60}")
        print("🏁 FINAL RESULTS")
        print(f"{'='*60}")
        print(f"User: {result['user_email']}")
        print(f"Success: {result['success']}")
        print(f"New User: {result['is_new_user']}")
        print(f"Emails Processed: {result['emails_processed']}")
        
        if result['error']:
            print(f"Error: {result['error']}")
        
        if result['success']:
            print("✅ User processing completed successfully!")
            print("📊 Check users.csv for user database")
        
    except Exception as e:
        print(f"❌ System error: {e}")

if __name__ == "__main__":
    main()