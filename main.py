# main.py - Fixed Agentic Email Labeling System with proper env loading
import os
import sys
from typing import Dict, List

# Fix environment loading FIRST, before other imports
from dotenv import load_dotenv

# Load environment variables with explicit path
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_result = load_dotenv(env_path)

print(f"🔧 Environment loading: {load_result}")
print(f"📂 Looking for .env at: {env_path}")

# Verify OpenAI key is loaded
openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    print(f"✅ OpenAI API key loaded: {openai_key[:20]}...")
else:
    print("❌ OpenAI API key not found!")
    print("🔍 Available environment variables:")
    for key in os.environ.keys():
        if 'OPENAI' in key or 'API' in key:
            print(f"   {key}: {os.environ[key][:20]}...")

# Now import other modules
try:
    from agno.team import Team
    from agno.models.openai import OpenAIChat
except ImportError as e:
    print(f"❌ Agno import error: {e}")
    print("💡 Install with: pip install agno")
    sys.exit(1)

from agents.email_fetcher_agent import EmailFetcherAgent
from agents.email_classifier_agent import EmailClassifierAgent
from agents.gmail_manager_agent import GmailManagerAgent
from agents.user_manager_agent import UserManagerAgent
from agents.history_checker_agent import HistoryCheckerAgent
from workflows.email_labeling_workflow import EmailLabelingWorkflow
from workflows.user_onboarding_workflow import UserOnboardingWorkflow
from utils.logging import setup_logging
from loguru import logger

class AgenticEmailSystem:
    """
    Agentic Email Labeling System
    
    Features:
    - User signup and credential management
    - Initial email classification for existing emails
    - Real-time email monitoring and labeling
    - 7-day rule for automatic history classification
    - Inbox management (only 'to do' emails remain in inbox)
    """
    
    def __init__(self):
        # Verify OpenAI API key before proceeding
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        # Setup logging
        setup_logging()
        
        # Initialize specialized agents
        try:
            self.user_manager = UserManagerAgent()
            self.email_fetcher = EmailFetcherAgent()
            self.history_checker = HistoryCheckerAgent()
            self.email_classifier = EmailClassifierAgent()
            self.gmail_manager = GmailManagerAgent()
            
            logger.info("✅ All agents initialized successfully")
        except Exception as e:
            logger.error(f"❌ Error initializing agents: {e}")
            raise
        
        # Initialize workflows
        try:
            self.user_onboarding_workflow = UserOnboardingWorkflow()
            self.email_labeling_workflow = EmailLabelingWorkflow()
            
            logger.info("✅ All workflows initialized successfully")
        except Exception as e:
            logger.error(f"❌ Error initializing workflows: {e}")
            raise
        
        # Create Agno team for coordinated email processing
        try:
            self.email_team = Team(
                name="Email Labeling Team",
                mode="coordinate",
                model=OpenAIChat(id="gpt-4o"),
                members=[
                    self.email_fetcher,
                    self.history_checker,
                    self.email_classifier,
                    self.gmail_manager
                ],
                instructions=[
                    "You are a specialized team for email labeling and management",
                    "Coordinate to efficiently process and label emails",
                    "Apply 7-day rule for history classification",
                    "Manage inbox visibility (only 'to do' emails in inbox)",
                    "Ensure proper label application and thread-based classification"
                ],
                show_tool_calls=True,
                markdown=True,
                debug_mode=False
            )
            
            # Create user management team
            self.user_team = Team(
                name="User Management Team",
                mode="coordinate", 
                model=OpenAIChat(id="gpt-4o"),
                members=[
                    self.user_manager,
                    self.gmail_manager
                ],
                instructions=[
                    "Handle user registration and authentication",
                    "Manage user credentials and data storage",
                    "Setup Gmail access and permissions",
                    "Coordinate initial user onboarding"
                ],
                show_tool_calls=True,
                markdown=True,
                debug_mode=False
            )
            
            logger.info("✅ Agno teams initialized successfully")
        except Exception as e:
            logger.error(f"❌ Error initializing Agno teams: {e}")
            # Continue without teams for now
            self.email_team = None
            self.user_team = None
        
        logger.info("🤖 Agentic Email System initialized")
    
    def register_new_user(self, user_email: str) -> Dict:
        """
        Register a new user with OAuth authentication
        
        Args:
            user_email: Email address of the user to register
            
        Returns:
            Dict with registration results
        """
        logger.info(f"Starting user registration for {user_email}")
        
        try:
            # Run user onboarding workflow
            results = self.user_onboarding_workflow.onboard_user(
                user_email=user_email,
                user_manager=self.user_manager,
                gmail_manager=self.gmail_manager
            )
            
            if results['success']:
                logger.info(f"User {user_email} registered successfully")
                
                # Trigger initial email processing
                initial_processing = self.process_existing_emails(user_email)
                results['initial_processing'] = initial_processing
                
            return results
            
        except Exception as e:
            logger.error(f"Error in user registration: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'user_email': user_email
            }
    
    def process_existing_emails(self, user_email: str, limit: int = 100) -> Dict:
        """
        Process and label existing emails for a user
        
        Args:
            user_email: User's email address
            limit: Maximum number of emails to process
            
        Returns:
            Dict with processing results
        """
        logger.info(f"Processing existing emails for {user_email} (limit: {limit})")
        
        try:
            # Use team if available, otherwise direct agent calls
            if self.email_team:
                results = self.email_labeling_workflow.process_existing_emails(
                    user_email=user_email,
                    email_limit=limit,
                    team=self.email_team
                )
            else:
                # Fallback to direct agent calls
                results = self._process_emails_direct(user_email, limit)
            
            logger.info(f"Processed {results.get('emails_processed', 0)} existing emails")
            return results
            
        except Exception as e:
            logger.error(f"Error processing existing emails: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'user_email': user_email
            }
    
    def _process_emails_direct(self, user_email: str, limit: int) -> Dict:
        """Direct email processing without Agno teams"""
        try:
            # Get user credentials
            credentials = self.user_manager.get_user_credentials(user_email)
            if not credentials:
                return {
                    'success': False,
                    'error': 'No credentials found for user'
                }
            
            # Fetch emails
            emails = self.email_fetcher.fetch_emails(credentials, limit=limit)
            if not emails:
                return {
                    'success': True,
                    'message': 'No emails found',
                    'emails_processed': 0
                }
            
            # Check ages
            age_results = self.history_checker.check_multiple_emails(emails)
            
            # Apply history labels
            history_count = 0
            if age_results['history_email_ids']:
                history_result = self.gmail_manager.apply_history_labels(
                    credentials, age_results['history_email_ids']
                )
                history_count = history_result.get('history_labels_applied', 0)
            
            # Classify recent emails
            classified_count = 0
            label_distribution = {}
            
            if age_results['recent_email_ids']:
                recent_emails = [e for e in emails if e.id in age_results['recent_email_ids']]
                classification_results = self.email_classifier.classify_emails(recent_emails)
                
                if classification_results['success']:
                    classifications = classification_results['classifications']
                    label_distribution = classification_results['label_distribution']
                    
                    # Apply labels
                    label_result = self.gmail_manager.apply_labels_to_emails(
                        credentials, classifications
                    )
                    classified_count = label_result.get('labels_applied', 0)
            
            # Update stats
            total_processed = history_count + classified_count
            self.user_manager.update_user_stats(
                user_email, 
                emails_processed=total_processed, 
                labels_applied=total_processed
            )
            
            if history_count > 0:
                label_distribution['history'] = history_count
            
            return {
                'success': True,
                'user_email': user_email,
                'emails_processed': total_processed,
                'emails_fetched': len(emails),
                'history_count': history_count,
                'classified_count': classified_count,
                'labels_applied': total_processed,
                'label_distribution': label_distribution
            }
            
        except Exception as e:
            logger.error(f"Error in direct processing: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_new_email(self, user_email: str, message_id: str) -> Dict:
        """
        Process and label a single new email
        
        Args:
            user_email: User's email address
            message_id: Gmail message ID
            
        Returns:
            Dict with processing results
        """
        logger.info(f"Processing new email {message_id} for {user_email}")
        
        try:
            # Use team if available, otherwise direct calls
            if self.email_team:
                results = self.email_labeling_workflow.process_single_email(
                    user_email=user_email,
                    message_id=message_id,
                    team=self.email_team
                )
            else:
                # Fallback to direct processing
                results = self._process_single_email_direct(user_email, message_id)
            
            logger.info(f"Processed new email: {results.get('label', 'unknown')} label applied")
            return results
            
        except Exception as e:
            logger.error(f"Error processing new email: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'user_email': user_email,
                'message_id': message_id
            }
    
    def _process_single_email_direct(self, user_email: str, message_id: str) -> Dict:
        """Direct single email processing"""
        try:
            credentials = self.user_manager.get_user_credentials(user_email)
            if not credentials:
                return {
                    'success': False,
                    'error': 'No credentials found'
                }
            
            # Fetch email
            email = self.email_fetcher.fetch_single_email(credentials, message_id)
            if not email:
                return {
                    'success': False,
                    'error': 'Could not fetch email'
                }
            
            # Check age
            age_result = self.history_checker.check_email_age(email)
            
            if age_result['is_history']:
                # Apply history
                self.gmail_manager.apply_history_labels(credentials, [message_id])
                return {
                    'success': True,
                    'label': 'history',
                    'confidence': 1.0,
                    'reasoning': age_result['reasoning']
                }
            
            # Classify
            thread_emails = self.email_fetcher.fetch_thread_emails(credentials, email.thread_id)
            classification = self.email_classifier.classify_single_email(email, thread_emails)
            
            if classification['success']:
                # Apply label
                self.gmail_manager.apply_labels_to_emails(credentials, [classification])
                self.user_manager.update_user_stats(user_email, emails_processed=1, labels_applied=1)
            
            return classification
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def start_email_monitoring(self, user_email: str) -> Dict:
        """
        Start real-time email monitoring for a user
        
        Args:
            user_email: User's email address
            
        Returns:
            Dict with monitoring setup results
        """
        logger.info(f"Starting email monitoring for {user_email}")
        
        try:
            # Check if user exists and is authenticated
            user_info = self.user_manager.get_user_info(user_email)
            if not user_info['exists']:
                return {
                    'success': False,
                    'error': 'User not registered',
                    'user_email': user_email
                }
            
            # Start monitoring (this would integrate with push notifications)
            monitoring_results = self.gmail_manager.setup_push_notifications(user_email)
            
            logger.info(f"Email monitoring started for {user_email}")
            return {
                'success': True,
                'user_email': user_email,
                'monitoring_active': True,
                'setup_results': monitoring_results
            }
            
        except Exception as e:
            logger.error(f"Error starting email monitoring: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'user_email': user_email
            }
    
    def get_user_stats(self, user_email: str) -> Dict:
        """
        Get processing statistics for a user
        
        Args:
            user_email: User's email address
            
        Returns:
            Dict with user statistics
        """
        try:
            user_info = self.user_manager.get_user_info(user_email)
            
            if not user_info['exists']:
                return {
                    'success': False,
                    'error': 'User not found',
                    'user_email': user_email
                }
            
            # Get email processing stats
            if self.email_labeling_workflow:
                stats = self.email_labeling_workflow.get_user_stats(user_email)
            else:
                # Fallback stats
                stats = {
                    'total_processed': user_info['total_emails_processed'],
                    'labels_applied': user_info['labels_applied'],
                    'last_processed': user_info['last_processed_at'],
                    'inbox_count': 0,
                    'monitoring_active': user_info['monitoring_active']
                }
            
            return {
                'success': True,
                'user_email': user_email,
                'user_info': user_info,
                'processing_stats': stats
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'user_email': user_email
            }
    
    def revert_user_labels(self, user_email: str) -> Dict:
        """
        Revert all applied labels for a user (for testing)
        
        Args:
            user_email: User's email address
            
        Returns:
            Dict with revert results
        """
        logger.info(f"Reverting labels for {user_email}")
        
        try:
            # Use Gmail manager to revert labels
            results = self.gmail_manager.revert_all_labels(user_email)
            
            # Clear user processing history
            self.user_manager.clear_processing_history(user_email)
            
            logger.info(f"Reverted labels for {user_email}")
            return results
            
        except Exception as e:
            logger.error(f"Error reverting labels: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'user_email': user_email
            }

def main():
    """Main entry point for the agentic email system"""
    
    print("🤖 Agentic Email Labeling System")
    print("=" * 50)
    
    # Check prerequisites
    print("Checking prerequisites...")
    
    # Check OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in environment variables!")
        print("📝 Please add OPENAI_API_KEY to your .env file")
        return
    
    print("✅ OpenAI API key found")
    
    # Check credentials.json
    if not os.path.exists('credentials.json'):
        print("❌ credentials.json not found!")
        print("📝 Please download from Google Cloud Console")
        return
    
    print("✅ Google credentials found")
    
    try:
        # Initialize the system
        email_system = AgenticEmailSystem()
        print("✅ Agentic email system initialized")
    except Exception as e:
        print(f"❌ Failed to initialize system: {e}")
        return
    
    # Example usage - replace with actual user email
    test_user_email = "gaurav@whizmail.ai"
    
    print(f"Testing with user: {test_user_email}")
    print("\nAvailable operations:")
    print("1. Register new user")
    print("2. Process existing emails")
    print("3. Start email monitoring")
    print("4. Get user stats")
    print("5. Revert labels (testing)")
    
    # Interactive menu
    while True:
        try:
            choice = input("\nEnter choice (1-5, or 'q' to quit): ").strip()
            
            if choice == 'q':
                print("👋 Goodbye!")
                break
                
            elif choice == '1':
                print(f"\n🔐 Registering user: {test_user_email}")
                results = email_system.register_new_user(test_user_email)
                
                if results['success']:
                    print("✅ User registration successful!")
                    print(f"   User email: {results['user_email']}")
                    print(f"   Credentials stored: {results.get('credentials_stored', 'Unknown')}")
                    
                    if 'initial_processing' in results:
                        proc = results['initial_processing']
                        print(f"   Initial emails processed: {proc.get('emails_processed', 0)}")
                        print(f"   Labels applied: {proc.get('labels_applied', 0)}")
                else:
                    print(f"❌ Registration failed: {results.get('error', 'Unknown error')}")
            
            elif choice == '2':
                email_limit = input("Enter email limit (default 50): ").strip()
                limit = int(email_limit) if email_limit.isdigit() else 50
                
                print(f"\n📧 Processing existing emails (limit: {limit})")
                results = email_system.process_existing_emails(test_user_email, limit)
                
                if results['success']:
                    print("✅ Email processing completed!")
                    print(f"   Emails processed: {results.get('emails_processed', 0)}")
                    print(f"   History emails: {results.get('history_count', 0)}")
                    print(f"   Classified emails: {results.get('classified_count', 0)}")
                    print(f"   To-do emails in inbox: {results.get('inbox_todo_count', 0)}")
                    
                    # Show label distribution
                    if 'label_distribution' in results:
                        print("\n   Label Distribution:")
                        for label, count in results['label_distribution'].items():
                            print(f"     {label}: {count}")
                else:
                    print(f"❌ Processing failed: {results.get('error', 'Unknown error')}")
            
            elif choice == '3':
                print(f"\n🔔 Starting email monitoring for {test_user_email}")
                results = email_system.start_email_monitoring(test_user_email)
                
                if results['success']:
                    print("✅ Email monitoring started!")
                    print("   New emails will be automatically labeled")
                    print("   Push notifications configured")
                else:
                    print(f"❌ Monitoring setup failed: {results.get('error', 'Unknown error')}")
            
            elif choice == '4':
                print(f"\n📊 Getting stats for {test_user_email}")
                results = email_system.get_user_stats(test_user_email)
                
                if results['success']:
                    user_info = results['user_info']
                    stats = results['processing_stats']
                    
                    print("✅ User Statistics:")
                    print(f"   Email: {user_info['email']}")
                    print(f"   Registered: {user_info.get('created_at', 'Unknown')}")
                    print(f"   Last processed: {user_info.get('last_processed_at', 'Never')}")
                    print(f"   Total emails processed: {stats.get('total_processed', 0)}")
                    print(f"   Current inbox count: {stats.get('inbox_count', 0)}")
                else:
                    print(f"❌ Stats retrieval failed: {results.get('error', 'Unknown error')}")
            
            elif choice == '5':
                confirm = input("⚠️  Are you sure you want to revert all labels? (y/N): ")
                if confirm.lower() == 'y':
                    print(f"\n🔄 Reverting labels for {test_user_email}")
                    results = email_system.revert_user_labels(test_user_email)
                    
                    if results['success']:
                        print("✅ Labels reverted successfully!")
                        print(f"   Reverted count: {results.get('reverted_count', 0)}")
                    else:
                        print(f"❌ Revert failed: {results.get('error', 'Unknown error')}")
                else:
                    print("❌ Revert cancelled")
            
            else:
                print("❌ Invalid choice. Please enter 1-5 or 'q'")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()