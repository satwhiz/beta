# enhanced_email_processor_fixed.py - Fixed version with timezone handling
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set, Optional
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import pytz

# Import our modules
from agents.thread_email_classifier import ThreadEmailClassifier
from tools.gmail_tools import GmailTools
from utils.thread_organizer import ThreadOrganizer
from models.email_models import EmailMessage, EmailLabel
from models.response_models import ThreadClassificationResponse

class FixedEmailProcessor:
    """Fixed email processor that handles timezone issues and labels ALL emails"""
    
    def __init__(self):
        load_dotenv()
        print("🔧 Initializing Fixed Email Processor...")
        
        # Initialize components
        self.classifier = ThreadEmailClassifier()
        self.thread_organizer = ThreadOrganizer()
        
        # Processing state
        self.user_credentials = {}
        self.processed_threads: Set[str] = set()
        self.processing_stats = {
            'total_emails': 0,
            'total_threads': 0,
            'emails_by_label': {},
            'threads_by_label': {},
            'processing_errors': 0,
            'successful_threads': 0
        }
        
        # History threshold (emails older than this go to History)
        self.history_days_threshold = 7
        
        print("✅ Fixed Email Processor initialized!")
    
    def authenticate_user(self, user_email: str) -> bool:
        """Authenticate a user for processing"""
        try:
            print(f"🔐 Authenticating {user_email}...")
            
            scopes = [
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.modify'
            ]
            
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes)
            credentials = flow.run_local_server(port=0, access_type='offline')
            
            # Test Gmail connection
            gmail_tools = GmailTools(credentials)
            profile = gmail_tools.get_profile()
            
            if profile.get('email') == user_email:
                self.user_credentials[user_email] = credentials
                print(f"✅ Authentication successful for {user_email}")
                print(f"📧 Connected to Gmail with {profile.get('total_messages', 0)} total messages")
                return True
            else:
                print(f"❌ Email mismatch: expected {user_email}, got {profile.get('email')}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def normalize_datetime(self, dt: datetime) -> datetime:
        """Normalize datetime to UTC timezone for consistent comparison"""
        if dt.tzinfo is None:
            # If naive datetime, assume it's UTC
            return pytz.UTC.localize(dt)
        else:
            # If timezone-aware, convert to UTC
            return dt.astimezone(pytz.UTC)
    
    def process_all_emails(self, user_email: str, email_limit: int = 500, apply_labels: bool = True) -> Dict:
        """
        Process ALL emails for a user with retroactive thread-based labeling - FIXED VERSION
        """
        try:
            if user_email not in self.user_credentials:
                print(f"❌ User {user_email} not authenticated")
                return {'success': False, 'error': 'User not authenticated'}
            
            credentials = self.user_credentials[user_email]
            gmail_tools = GmailTools(credentials)
            
            print(f"\n{'='*60}")
            print(f"🚀 FIXED EMAIL PROCESSING FOR {user_email}")
            print(f"{'='*60}")
            print(f"📊 Email limit: {email_limit}")
            print(f"📅 History threshold: {self.history_days_threshold} days")
            print(f"🏷️  Apply labels: {'Yes' if apply_labels else 'No (dry run)'}")
            
            # Step 1: Fetch all emails
            print(f"\n📧 Step 1: Fetching emails...")
            all_emails = gmail_tools.fetch_emails(limit=email_limit)
            
            if not all_emails:
                return {'success': False, 'error': 'No emails fetched'}
            
            print(f"✅ Fetched {len(all_emails)} emails")
            self.processing_stats['total_emails'] = len(all_emails)
            
            # Step 2: Organize emails by threads
            print(f"\n🧵 Step 2: Organizing emails by threads...")
            threads = self.thread_organizer.organize_emails_by_thread(all_emails)
            thread_info = self.thread_organizer.get_thread_info(threads)
            thread_stats = self.thread_organizer.get_thread_statistics(threads)
            
            print(f"✅ Organized into {len(threads)} threads")
            print(f"📊 Thread Statistics:")
            print(f"   • Single email threads: {thread_stats['single_email_threads']}")
            print(f"   • Multi-email threads: {thread_stats['multi_email_threads']}")
            print(f"   • Longest thread: {thread_stats['longest_thread']} emails")
            print(f"   • Average emails per thread: {thread_stats['avg_emails_per_thread']}")
            
            self.processing_stats['total_threads'] = len(threads)
            
            # Step 3: Process threads with FIXED logic
            print(f"\n🏷️  Step 3: Classifying threads with FIXED logic...")
            thread_results = self._process_threads_fixed(threads, apply_labels, gmail_tools)
            
            # Step 4: Apply labels to all emails in each thread
            print(f"\n📎 Step 4: Applying thread labels to all emails...")
            email_results = self._apply_thread_labels_to_emails(threads, thread_results, apply_labels, gmail_tools)
            
            # Step 5: Generate comprehensive report
            print(f"\n📊 Step 5: Generating processing report...")
            final_report = self._generate_processing_report(thread_results, email_results, thread_stats)
            
            return {
                'success': True,
                'user_email': user_email,
                'processing_stats': self.processing_stats,
                'thread_results': thread_results,
                'email_results': email_results,
                'final_report': final_report,
                'applied_labels': apply_labels
            }
            
        except Exception as e:
            print(f"❌ Error processing emails: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def _process_threads_fixed(self, threads: Dict[str, List[EmailMessage]], 
                             apply_labels: bool, gmail_tools: GmailTools) -> List[Dict]:
        """Process threads with FIXED timezone handling"""
        
        thread_results = []
        
        # Get current time in UTC for consistent comparison
        now_utc = datetime.now(pytz.UTC)
        cutoff_date = now_utc - timedelta(days=self.history_days_threshold)
        
        print(f"🕐 Current time (UTC): {now_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"📅 History cutoff (UTC): {cutoff_date.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        for i, (thread_id, thread_emails) in enumerate(threads.items()):
            try:
                print(f"\n🔄 Processing thread {i+1}/{len(threads)}: {thread_id}")
                
                # Sort emails by date for proper chronological analysis
                sorted_emails = sorted(thread_emails, key=lambda x: x.date)
                latest_email = sorted_emails[-1]
                
                print(f"   📧 Thread has {len(thread_emails)} emails")
                print(f"   📋 Subject: {latest_email.subject[:50]}...")
                
                # FIXED: Normalize datetime for comparison
                try:
                    latest_email_normalized = self.normalize_datetime(latest_email.date)
                    print(f"   📅 Latest email (UTC): {latest_email_normalized.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                    
                    # Enhanced classification logic with FIXED datetime comparison
                    if latest_email_normalized < cutoff_date:
                        # Automatic History classification for old emails
                        classification_result = {
                            'thread_id': thread_id,
                            'label': EmailLabel.HISTORY,
                            'confidence': 1.0,
                            'reasoning': f"Thread is older than {self.history_days_threshold} days - automatic History classification",
                            'email_count': len(thread_emails),
                            'classification_method': 'automatic_history'
                        }
                        print(f"   🏷️  → HISTORY (automatic - older than {self.history_days_threshold} days)")
                        
                    else:
                        # Thread-based classification using full context
                        print(f"   🧠 Analyzing thread context...")
                        
                        # Use our thread classifier
                        classifications = self.classifier.classify_multiple_threads({thread_id: sorted_emails})
                        
                        if classifications:
                            classification = classifications[0]
                            classification_result = {
                                'thread_id': thread_id,
                                'label': classification.label,
                                'confidence': classification.confidence,
                                'reasoning': classification.reasoning,
                                'email_count': len(thread_emails),
                                'classification_method': 'thread_context_analysis'
                            }
                            print(f"   🏷️  → {classification.label.value.upper()} (confidence: {classification.confidence:.2f})")
                            print(f"   💭 Reasoning: {classification.reasoning[:80]}...")
                        else:
                            # Fallback classification
                            classification_result = {
                                'thread_id': thread_id,
                                'label': EmailLabel.FYI,
                                'confidence': 0.5,
                                'reasoning': "Fallback classification - unable to determine specific category",
                                'email_count': len(thread_emails),
                                'classification_method': 'fallback'
                            }
                            print(f"   🏷️  → FYI (fallback)")
                    
                    # Update statistics
                    label_value = classification_result['label'].value
                    if label_value not in self.processing_stats['threads_by_label']:
                        self.processing_stats['threads_by_label'][label_value] = 0
                    self.processing_stats['threads_by_label'][label_value] += 1
                    
                    # Add thread info
                    classification_result.update({
                        'thread_emails': [email.id for email in thread_emails],
                        'participants': list(set([email.from_email for email in thread_emails] + 
                                               [email for email_obj in thread_emails for email in email_obj.to_emails])),
                        'date_range': {
                            'start': sorted_emails[0].date.isoformat(),
                            'end': sorted_emails[-1].date.isoformat()
                        }
                    })
                    
                    thread_results.append(classification_result)
                    self.processing_stats['successful_threads'] += 1
                    
                except Exception as date_error:
                    print(f"   ❌ DateTime error for thread {thread_id}: {date_error}")
                    print(f"   📅 Raw date: {latest_email.date}")
                    print(f"   📅 Date type: {type(latest_email.date)}")
                    
                    # Fallback: classify as FYI if we can't determine age
                    classification_result = {
                        'thread_id': thread_id,
                        'label': EmailLabel.FYI,
                        'confidence': 0.3,
                        'reasoning': f"DateTime processing error - fallback classification: {str(date_error)}",
                        'email_count': len(thread_emails),
                        'classification_method': 'error_fallback'
                    }
                    
                    classification_result.update({
                        'thread_emails': [email.id for email in thread_emails],
                        'participants': [],
                        'date_range': {'start': 'unknown', 'end': 'unknown'}
                    })
                    
                    thread_results.append(classification_result)
                    self.processing_stats['processing_errors'] += 1
                    
                    # Update statistics for fallback
                    label_value = classification_result['label'].value
                    if label_value not in self.processing_stats['threads_by_label']:
                        self.processing_stats['threads_by_label'][label_value] = 0
                    self.processing_stats['threads_by_label'][label_value] += 1
                
            except Exception as e:
                print(f"   ❌ General error processing thread {thread_id}: {e}")
                self.processing_stats['processing_errors'] += 1
                continue
        
        print(f"\n✅ Thread processing summary:")
        print(f"   • Successful: {self.processing_stats['successful_threads']}")
        print(f"   • Errors: {self.processing_stats['processing_errors']}")
        print(f"   • Total: {len(threads)}")
        
        return thread_results
    
    def _apply_thread_labels_to_emails(self, threads: Dict[str, List[EmailMessage]], 
                                     thread_results: List[Dict], apply_labels: bool, 
                                     gmail_tools: GmailTools) -> Dict:
        """Apply thread classification labels to ALL emails in each thread"""
        
        email_results = {
            'emails_labeled': 0,
            'emails_skipped': 0,
            'labeling_errors': 0,
            'label_details': []
        }
        
        # Create mapping of thread_id to classification
        thread_classifications = {result['thread_id']: result for result in thread_results}
        
        print(f"\n📊 Applying labels to emails:")
        print(f"   • Threads to process: {len(thread_classifications)}")
        print(f"   • Apply mode: {'LIVE' if apply_labels else 'DRY RUN'}")
        
        for thread_id, thread_emails in threads.items():
            if thread_id not in thread_classifications:
                print(f"   ⚠️ Skipping thread {thread_id} - no classification available")
                email_results['emails_skipped'] += len(thread_emails)
                continue
            
            classification = thread_classifications[thread_id]
            label_value = classification['label'].value
            
            print(f"\n📎 Thread {thread_id}: Applying '{label_value}' to {len(thread_emails)} emails")
            
            for email in thread_emails:
                try:
                    if apply_labels:
                        # Actually apply the label to Gmail
                        label_success = gmail_tools.apply_label(email.id, label_value)
                        
                        if label_success:
                            email_results['emails_labeled'] += 1
                            print(f"   ✅ Labeled {email.id}: {email.subject[:40]}...")
                        else:
                            email_results['labeling_errors'] += 1
                            print(f"   ❌ Failed to label {email.id}")
                    else:
                        # Dry run - just record what would be done
                        email_results['emails_labeled'] += 1
                        print(f"   📋 Would label {email.id}: {email.subject[:40]}...")
                    
                    # Update email statistics
                    if label_value not in self.processing_stats['emails_by_label']:
                        self.processing_stats['emails_by_label'][label_value] = 0
                    self.processing_stats['emails_by_label'][label_value] += 1
                    
                    # Record details
                    email_results['label_details'].append({
                        'email_id': email.id,
                        'thread_id': thread_id,
                        'subject': email.subject,
                        'from_email': email.from_email,
                        'label_applied': label_value,
                        'confidence': classification['confidence'],
                        'applied_successfully': apply_labels
                    })
                    
                except Exception as e:
                    print(f"   ❌ Error labeling email {email.id}: {e}")
                    email_results['labeling_errors'] += 1
        
        print(f"\n✅ Email labeling summary:")
        print(f"   • Emails labeled: {email_results['emails_labeled']}")
        print(f"   • Emails skipped: {email_results['emails_skipped']}")
        print(f"   • Labeling errors: {email_results['labeling_errors']}")
        
        return email_results
    
    def _generate_processing_report(self, thread_results: List[Dict], 
                                  email_results: Dict, thread_stats: Dict) -> Dict:
        """Generate comprehensive processing report"""
        
        # Calculate label distribution
        total_threads = len(thread_results)
        total_emails = email_results['emails_labeled'] + email_results['emails_skipped'] + email_results['labeling_errors']
        
        report = {
            'processing_summary': {
                'total_threads_processed': total_threads,
                'total_emails_processed': total_emails,
                'emails_successfully_labeled': email_results['emails_labeled'],
                'emails_skipped': email_results['emails_skipped'],
                'labeling_errors': email_results['labeling_errors'],
                'processing_errors': self.processing_stats['processing_errors'],
                'successful_threads': self.processing_stats['successful_threads']
            },
            'label_distribution': {
                'by_threads': self.processing_stats['threads_by_label'],
                'by_emails': self.processing_stats['emails_by_label']
            },
            'thread_statistics': thread_stats,
            'classification_methods': {}
        }
        
        # Count classification methods
        for result in thread_results:
            method = result['classification_method']
            if method not in report['classification_methods']:
                report['classification_methods'][method] = 0
            report['classification_methods'][method] += 1
        
        return report

def main():
    """Main function for FIXED enhanced email processing"""
    print("🛠️  FIXED Enhanced Email Processing System")
    print("=" * 50)
    print("This FIXED system will:")
    print("  🧵 Analyze ALL your emails by thread context")
    print("  📅 Handle timezone issues properly")
    print("  🏷️  Apply thread-based labels to ALL emails in each thread")
    print("  📊 Provide comprehensive processing statistics")
    print("  🔧 Actually apply labels (unlike before!)")
    
    # Initialize processor
    processor = FixedEmailProcessor()
    
    # Get user email
    default_user = "gaurav@whizmail.ai"
    user_email = input(f"\nEnter user email (default: {default_user}): ").strip()
    if not user_email:
        user_email = default_user
    
    # Authenticate user
    if not processor.authenticate_user(user_email):
        print("❌ Authentication failed. Exiting.")
        return
    
    # Get processing parameters
    print(f"\n🔧 Processing Configuration:")
    
    email_limit_input = input("Enter email limit (default: 50, recommended for testing): ").strip()
    email_limit = int(email_limit_input) if email_limit_input else 50
    
    dry_run_input = input("Dry run mode? (y/N - 'n' will ACTUALLY apply labels): ").lower()
    apply_labels = dry_run_input != 'y'
    
    print(f"\n📋 Configuration Summary:")
    print(f"   User: {user_email}")
    print(f"   Email limit: {email_limit}")
    print(f"   Mode: {'LIVE - Will apply labels to Gmail' if apply_labels else 'DRY RUN - No labels applied'}")
    print(f"   History threshold: 7 days")
    
    # Final confirmation
    confirm = input(f"\nProceed with FIXED processing? (y/N): ").lower()
    if confirm != 'y':
        print("❌ Processing cancelled")
        return
    
    # Process all emails
    print(f"\n🚀 Starting FIXED email processing...")
    start_time = datetime.now()
    
    result = processor.process_all_emails(user_email, email_limit, apply_labels)
    
    end_time = datetime.now()
    processing_time = end_time - start_time
    
    # Display results
    if result['success']:
        print(f"\n{'='*60}")
        print("🎉 FIXED PROCESSING COMPLETED SUCCESSFULLY!")
        print(f"{'='*60}")
        
        report = result['final_report']
        summary = report['processing_summary']
        
        print(f"⏱️  Processing time: {processing_time}")
        print(f"📊 Threads processed: {summary['total_threads_processed']}")
        print(f"📧 Emails processed: {summary['total_emails_processed']}")
        print(f"✅ Emails labeled: {summary['emails_successfully_labeled']}")
        print(f"❌ Errors: {summary['labeling_errors'] + summary['processing_errors']}")
        
        print(f"\n🏷️  Label Distribution (Threads):")
        for label, count in report['label_distribution']['by_threads'].items():
            percentage = (count / summary['total_threads_processed'] * 100) if summary['total_threads_processed'] > 0 else 0
            print(f"   {label.upper():15}: {count:4} threads ({percentage:5.1f}%)")
        
        print(f"\n🏷️  Label Distribution (Emails):")
        for label, count in report['label_distribution']['by_emails'].items():
            percentage = (count / summary['total_emails_processed'] * 100) if summary['total_emails_processed'] > 0 else 0
            print(f"   {label.upper():15}: {count:4} emails  ({percentage:5.1f}%)")
        
        if apply_labels:
            print(f"\n✅ All labels have been applied to your Gmail account!")
            print(f"📧 Check your Gmail sidebar to see the organized emails")
        else:
            print(f"\n📋 This was a dry run - no labels were actually applied")
            print(f"🔄 Run again with 'n' for dry run to apply labels")
        
    else:
        print(f"\n❌ Processing failed: {result['error']}")

if __name__ == "__main__":
    main()