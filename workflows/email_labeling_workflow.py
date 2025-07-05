# workflows/email_labeling_workflow.py - Fixed for Agno framework
from typing import Dict, List
from loguru import logger

class EmailLabelingWorkflow:
    """Workflow for processing and labeling emails"""
    
    def __init__(self):
        self.workflow_name = "Email Labeling"
    
    def process_existing_emails(self, user_email: str, email_limit: int, team) -> Dict:
        """
        Process and label existing emails for a user
        
        Args:
            user_email: User's email address
            email_limit: Maximum number of emails to process
            team: Agno team with email processing agents (or None for direct calls)
            
        Returns:
            Dict with processing results
        """
        try:
            logger.info(f"Starting email labeling workflow for {user_email}")
            
            # Get user credentials
            from agents.user_manager_agent import UserManagerAgent
            user_manager = UserManagerAgent()
            credentials = user_manager.get_user_credentials(user_email)
            
            if not credentials:
                return {
                    'success': False,
                    'error': 'No credentials found for user',
                    'user_email': user_email
                }
            
            # Initialize agents directly (bypass team for now)
            from agents.email_fetcher_agent import EmailFetcherAgent
            from agents.history_checker_agent import HistoryCheckerAgent
            from agents.email_classifier_agent import EmailClassifierAgent
            from agents.gmail_manager_agent import GmailManagerAgent
            
            email_fetcher = EmailFetcherAgent()
            history_checker = HistoryCheckerAgent()
            email_classifier = EmailClassifierAgent()
            gmail_manager = GmailManagerAgent()
            
            # Step 1: Fetch emails
            logger.info(f"Step 1: Fetching emails (limit: {email_limit})")
            emails = email_fetcher.fetch_emails(credentials, limit=email_limit)
            
            if not emails:
                return {
                    'success': True,
                    'message': 'No emails found to process',
                    'emails_processed': 0,
                    'user_email': user_email
                }
            
            logger.info(f"✅ Fetched {len(emails)} emails")
            
            # Step 2: Check email ages (7-day rule)
            logger.info("Step 2: Checking email ages for history classification")
            age_results = history_checker.check_multiple_emails(emails)
            
            history_email_ids = age_results['history_email_ids']
            recent_email_ids = age_results['recent_email_ids']
            
            logger.info(f"✅ Age check: {len(history_email_ids)} history, {len(recent_email_ids)} recent")
            
            # Step 3: Apply history labels to old emails
            history_labels_applied = 0
            if history_email_ids:
                logger.info(f"Step 3a: Applying history labels to {len(history_email_ids)} old emails")
                history_result = gmail_manager.apply_history_labels(credentials, history_email_ids)
                history_labels_applied = history_result.get('history_labels_applied', 0)
                logger.info(f"✅ Applied history labels to {history_labels_applied} emails")
            
            # Step 4: Classify recent emails
            classified_count = 0
            label_distribution = {}
            classifications = []
            
            if recent_email_ids:
                logger.info(f"Step 4: Classifying {len(recent_email_ids)} recent emails")
                
                # Get recent emails only
                recent_emails = [e for e in emails if e.id in recent_email_ids]
                
                # Classify emails
                classification_results = email_classifier.classify_emails(recent_emails)
                
                if classification_results['success']:
                    classifications = classification_results['classifications']
                    label_distribution = classification_results['label_distribution']
                    
                    logger.info(f"✅ Classified {len(classifications)} emails")
                    logger.info(f"Label distribution: {label_distribution}")
                    
                    # Step 5: Apply labels to Gmail
                    if classifications:
                        logger.info(f"Step 5: Applying labels to {len(classifications)} emails")
                        label_result = gmail_manager.apply_labels_to_emails(credentials, classifications)
                        
                        classified_count = label_result.get('labels_applied', 0)
                        inbox_modifications = label_result.get('inbox_modifications', 0)
                        
                        logger.info(f"✅ Applied {classified_count} labels")
                        logger.info(f"✅ Modified inbox for {inbox_modifications} emails")
                else:
                    logger.error(f"Classification failed: {classification_results.get('error', 'Unknown error')}")
            
            # Step 6: Update user statistics
            total_processed = history_labels_applied + classified_count
            total_labels_applied = history_labels_applied + classified_count
            
            user_manager.update_user_stats(
                user_email, 
                emails_processed=total_processed, 
                labels_applied=total_labels_applied
            )
            
            # Add history to label distribution
            if history_labels_applied > 0:
                label_distribution['history'] = history_labels_applied
            
            # Step 7: Get inbox statistics
            inbox_emails = [c for c in classifications if c.get('label') == 'to do']
            
            result = {
                'success': True,
                'user_email': user_email,
                'emails_processed': total_processed,
                'emails_fetched': len(emails),
                'history_count': history_labels_applied,
                'classified_count': classified_count,
                'labels_applied': total_labels_applied,
                'label_distribution': label_distribution,
                'inbox_todo_count': len(inbox_emails),
                'workflow_steps_completed': 6
            }
            
            logger.info(f"✅ Email labeling workflow completed for {user_email}")
            logger.info(f"Processed: {total_processed} emails, Applied: {total_labels_applied} labels")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in email labeling workflow: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'user_email': user_email
            }
    
    def process_single_email(self, user_email: str, message_id: str, team) -> Dict:
        """
        Process and label a single new email
        
        Args:
            user_email: User's email address
            message_id: Gmail message ID
            team: Agno team with email processing agents (or None for direct calls)
            
        Returns:
            Dict with processing results
        """
        try:
            logger.info(f"Processing single email {message_id} for {user_email}")
            
            # Get user credentials
            from agents.user_manager_agent import UserManagerAgent
            user_manager = UserManagerAgent()
            credentials = user_manager.get_user_credentials(user_email)
            
            if not credentials:
                return {
                    'success': False,
                    'error': 'No credentials found for user',
                    'user_email': user_email,
                    'message_id': message_id
                }
            
            # Initialize agents directly
            from agents.email_fetcher_agent import EmailFetcherAgent
            from agents.history_checker_agent import HistoryCheckerAgent
            from agents.email_classifier_agent import EmailClassifierAgent
            from agents.gmail_manager_agent import GmailManagerAgent
            
            email_fetcher = EmailFetcherAgent()
            history_checker = HistoryCheckerAgent()
            email_classifier = EmailClassifierAgent()
            gmail_manager = GmailManagerAgent()
            
            # Step 1: Fetch the email
            email = email_fetcher.fetch_single_email(credentials, message_id)
            
            if not email:
                return {
                    'success': False,
                    'error': 'Could not fetch email',
                    'user_email': user_email,
                    'message_id': message_id
                }
            
            # Step 2: Check email age
            age_result = history_checker.check_email_age(email)
            
            if age_result['is_history']:
                # Apply history label
                history_result = gmail_manager.apply_history_labels(credentials, [message_id])
                
                result = {
                    'success': True,
                    'user_email': user_email,
                    'message_id': message_id,
                    'subject': email.subject,
                    'label': 'history',
                    'confidence': 1.0,
                    'reasoning': age_result['reasoning'],
                    'removed_from_inbox': True,
                    'days_old': age_result['days_old']
                }
                
                logger.info(f"Email {message_id} classified as history (age: {age_result['days_old']} days)")
                return result
            
            # Step 3: Classify recent email
            # Get thread context
            thread_emails = email_fetcher.fetch_thread_emails(credentials, email.thread_id)
            
            # Classify
            classification = email_classifier.classify_single_email(email, thread_emails)
            
            if not classification['success']:
                return {
                    'success': False,
                    'error': f"Classification failed: {classification.get('error', 'Unknown error')}",
                    'user_email': user_email,
                    'message_id': message_id
                }
            
            # Step 4: Apply label
            label_result = gmail_manager.apply_labels_to_emails(credentials, [classification])
            
            # Step 5: Update user stats
            if label_result['success']:
                user_manager.update_user_stats(user_email, emails_processed=1, labels_applied=1)
            
            result = {
                'success': True,
                'user_email': user_email,
                'message_id': message_id,
                'subject': email.subject,
                'label': classification['label'],
                'confidence': classification['confidence'],
                'reasoning': classification['reasoning'],
                'removed_from_inbox': (classification['label'] != 'to do'),
                'thread_email_count': classification['thread_email_count']
            }
            
            logger.info(f"Email {message_id} classified as {classification['label']}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing single email: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'user_email': user_email,
                'message_id': message_id
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
            from agents.user_manager_agent import UserManagerAgent
            user_manager = UserManagerAgent()
            
            # Get user info
            user_info = user_manager.get_user_info(user_email)
            
            if not user_info['exists']:
                return {
                    'error': 'User not found',
                    'user_email': user_email
                }
            
            # Get Gmail stats if possible
            credentials = user_manager.get_user_credentials(user_email)
            inbox_count = 0
            
            if credentials:
                try:
                    from agents.gmail_manager_agent import GmailManagerAgent
                    gmail_manager = GmailManagerAgent()
                    inbox_status = gmail_manager.get_inbox_status(credentials)
                    inbox_count = inbox_status.get('inbox_count', 0)
                except Exception as e:
                    logger.warning(f"Could not get inbox status: {e}")
                    pass  # Skip if Gmail access fails
            
            return {
                'total_processed': user_info['total_emails_processed'],
                'labels_applied': user_info['labels_applied'],
                'last_processed': user_info['last_processed_at'],
                'inbox_count': inbox_count,
                'monitoring_active': user_info['monitoring_active']
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}")
            return {
                'error': str(e),
                'user_email': user_email
            }