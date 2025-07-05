# label_mapping_fix.py - Fix duplicate label creation
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from tools.gmail_tools import GmailTools
from agents.thread_email_classifier import ThreadEmailClassifier
from utils.thread_organizer import ThreadOrganizer
import pytz

class FixedLabelManager:
    """Fixed label manager that uses correct emoji label names"""
    
    # Map classification labels to actual Gmail label names
    LABEL_MAPPING = {
        'to do': '📋 To Do',
        'awaiting reply': '⏳ Awaiting Reply',
        'fyi': 'ℹ️ FYI', 
        'done': '✅ Done',
        'spam': '🗑️ SPAM',
        'history': '📜 History'
    }
    
    def __init__(self, gmail_tools):
        self.gmail_tools = gmail_tools
        self.existing_labels = self._get_existing_labels()
        print(f"📋 Found {len(self.existing_labels)} existing labels")
    
    def _get_existing_labels(self):
        """Get all existing Gmail labels"""
        try:
            labels = self.gmail_tools.get_labels()
            label_dict = {label['name']: label['id'] for label in labels}
            return label_dict
        except Exception as e:
            print(f"❌ Error getting labels: {e}")
            return {}
    
    def apply_label_fixed(self, email_id: str, classification_label: str) -> bool:
        """Apply label using correct emoji label name"""
        try:
            # Map classification result to actual Gmail label name
            actual_label_name = self.LABEL_MAPPING.get(classification_label, classification_label)
            
            # Check if the label exists
            if actual_label_name not in self.existing_labels:
                print(f"⚠️ Label '{actual_label_name}' not found! Available labels:")
                for label_name in self.existing_labels.keys():
                    if any(keyword in label_name.lower() for keyword in ['to do', 'awaiting', 'fyi', 'done', 'spam', 'history']):
                        print(f"   • {label_name}")
                
                # Try to find similar label
                similar_label = self._find_similar_label(classification_label)
                if similar_label:
                    print(f"   🔄 Using similar label: {similar_label}")
                    actual_label_name = similar_label
                else:
                    print(f"   ❌ No similar label found for '{classification_label}'")
                    return False
            
            # Apply the label using the label ID
            label_id = self.existing_labels[actual_label_name]
            
            # Use Gmail API directly to avoid label creation
            try:
                self.gmail_tools.service.users().messages().modify(
                    userId='me',
                    id=email_id,
                    body={'addLabelIds': [label_id]}
                ).execute()
                
                print(f"   ✅ Applied '{actual_label_name}' to email {email_id}")
                return True
                
            except Exception as e:
                print(f"   ❌ Failed to apply label: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Label application error: {e}")
            return False
    
    def _find_similar_label(self, classification_label: str) -> str:
        """Find similar existing label"""
        classification_lower = classification_label.lower()
        
        for label_name in self.existing_labels.keys():
            label_lower = label_name.lower()
            
            # Check for keyword matches
            if classification_lower == 'to do' and ('to do' in label_lower or 'todo' in label_lower):
                return label_name
            elif classification_lower == 'awaiting reply' and 'awaiting' in label_lower:
                return label_name
            elif classification_lower == 'fyi' and 'fyi' in label_lower:
                return label_name
            elif classification_lower == 'done' and 'done' in label_lower and 'undone' not in label_lower:
                return label_name
            elif classification_lower == 'spam' and ('spam' in label_lower or '🗑️' in label_name):
                return label_name
            elif classification_lower == 'history' and 'history' in label_lower:
                return label_name
        
        return None

def fixed_email_labeling():
    """Fixed email labeling that won't create duplicate labels"""
    
    print("🔧 FIXED Email Labeling (No Duplicate Labels)")
    print("=" * 50)
    print("This FIXED version will:")
    print("  🧵 Use your EXISTING emoji labels")
    print("  🚫 NOT create duplicate text labels")
    print("  🔍 Map classification results to correct label names")
    
    # Load environment
    load_dotenv()
    
    # Authenticate
    user_email = "gaurav@whizmail.ai"
    
    print(f"\n🔐 Authenticating {user_email}...")
    
    scopes = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ]
    
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes)
    credentials = flow.run_local_server(port=0, access_type='offline')
    
    print("✅ Authentication successful")
    
    # Initialize tools
    gmail_tools = GmailTools(credentials)
    classifier = ThreadEmailClassifier()
    organizer = ThreadOrganizer()
    
    # Initialize FIXED label manager
    label_manager = FixedLabelManager(gmail_tools)
    
    # Check if our labels exist
    print(f"\n🔍 Checking for emoji labels...")
    required_labels = ['📋 To Do', '⏳ Awaiting Reply', 'ℹ️ FYI', '✅ Done', '🗑️ SPAM', '📜 History']
    missing_labels = []
    
    for label in required_labels:
        if label in label_manager.existing_labels:
            print(f"   ✅ Found: {label}")
        else:
            print(f"   ❌ Missing: {label}")
            missing_labels.append(label)
    
    if missing_labels:
        print(f"\n⚠️ Missing {len(missing_labels)} labels!")
        print("🔧 Please run: python setup_labels.py")
        return
    
    # Get emails
    email_limit = int(input("\nHow many recent emails to process? (default: 20): ") or "20")
    
    print(f"\n📧 Fetching {email_limit} recent emails...")
    emails = gmail_tools.fetch_emails(limit=email_limit)
    
    if not emails:
        print("❌ No emails found")
        return
    
    print(f"✅ Found {len(emails)} emails")
    
    # Organize by threads
    print("\n🧵 Organizing by threads...")
    threads = organizer.organize_emails_by_thread(emails)
    
    print(f"✅ Found {len(threads)} threads")
    
    # Process each thread
    print(f"\n🏷️ Processing threads with FIXED label mapping...")
    
    # History cutoff (7 days)
    cutoff_date = datetime.now(pytz.UTC) - timedelta(days=7)
    
    labeled_count = 0
    error_count = 0
    label_stats = {}
    
    for i, (thread_id, thread_emails) in enumerate(threads.items()):
        try:
            print(f"\n🔄 Thread {i+1}/{len(threads)}: {len(thread_emails)} emails")
            
            # Get latest email
            latest_email = max(thread_emails, key=lambda x: x.date)
            print(f"   📋 Subject: {latest_email.subject[:50]}...")
            
            # Handle timezone
            if latest_email.date.tzinfo is None:
                email_date = pytz.UTC.localize(latest_email.date)
            else:
                email_date = latest_email.date.astimezone(pytz.UTC)
            
            # Determine label
            if email_date < cutoff_date:
                classification_label = "history"
                actual_label = "📜 History"
                print(f"   🏷️ → HISTORY (old)")
            else:
                # Classify using AI
                classifications = classifier.classify_multiple_threads({thread_id: thread_emails})
                
                if classifications:
                    classification = classifications[0]
                    classification_label = classification.label.value
                    actual_label = label_manager.LABEL_MAPPING[classification_label]
                    print(f"   🏷️ → {actual_label} ({classification.confidence:.2f})")
                else:
                    classification_label = "fyi"
                    actual_label = "ℹ️ FYI"
                    print(f"   🏷️ → ℹ️ FYI (fallback)")
            
            # Update stats
            if actual_label not in label_stats:
                label_stats[actual_label] = 0
            
            # Apply label to ALL emails in thread using FIXED method
            thread_success = 0
            for email in thread_emails:
                try:
                    success = label_manager.apply_label_fixed(email.id, classification_label)
                    if success:
                        thread_success += 1
                        labeled_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    error_count += 1
                    print(f"     ❌ Error: {e}")
            
            label_stats[actual_label] += thread_success
            print(f"   ✅ Successfully labeled {thread_success}/{len(thread_emails)} emails in thread")
            
        except Exception as e:
            print(f"   ❌ Thread error: {e}")
            error_count += len(thread_emails)
    
    # Summary
    print(f"\n{'='*50}")
    print("🎉 FIXED LABELING COMPLETED!")
    print(f"{'='*50}")
    print(f"✅ Emails labeled: {labeled_count}")
    print(f"❌ Errors: {error_count}")
    print(f"🧵 Threads processed: {len(threads)}")
    
    print(f"\n🏷️ Label Distribution:")
    for label, count in label_stats.items():
        print(f"   {label}: {count} emails")
    
    if labeled_count > 0:
        print(f"\n📧 Check your Gmail - {labeled_count} emails now have EMOJI labels!")
        print("🚫 No duplicate text labels were created!")
    
    print(f"\n💡 All labels use emoji names:")
    for text_label, emoji_label in label_manager.LABEL_MAPPING.items():
        print(f"   '{text_label}' → '{emoji_label}'")

if __name__ == "__main__":
    fixed_email_labeling()