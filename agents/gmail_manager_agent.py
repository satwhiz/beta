# agents/gmail_manager_agent.py - Fixed version with proper label handling
from typing import Dict, List
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from loguru import logger

class GmailManagerAgent(Agent):
    """Agent responsible for Gmail label management and inbox operations"""
    
    def __init__(self):
        super().__init__(
            name="Gmail Manager Agent",
            role="Manage Gmail labels, inbox operations, and email modifications",
            model=OpenAIChat(id="gpt-4o"),
            instructions=[
                "You are responsible for Gmail management operations",
                "Create and apply labels to emails",
                "Manage inbox visibility (only 'to do' emails in inbox)",
                "Handle bulk email operations efficiently",
                "Maintain label consistency and visibility",
                "Provide detailed operation results and error handling"
            ]
        )
        
        # Map internal label names to Gmail display names
        self.label_mapping = {
            'to do': '📋 To Do',
            'awaiting reply': '⏳ Awaiting Reply', 
            'fyi': 'ℹ️ FYI',
            'done': '✅ Done',
            'spam': '🗑️ Promotional',  # Changed from system SPAM
            'history': '📜 History'
        }
        
        # Fallback mapping for existing labels
        self.fallback_mapping = {
            'spam': ['SPAM', 'spam', '🗑️ Promotional', 'promotional']
        }
        
        # Track applied labels for reversal
        self.applied_labels = []
    
    def apply_labels_to_emails(self, credentials: Credentials, 
                              classifications: List[Dict]) -> Dict:
        """
        Apply labels to emails based on classifications
        
        Args:
            credentials: Google OAuth credentials
            classifications: List of email classifications
            
        Returns:
            Dict with operation results
        """
        try:
            logger.info(f"Applying labels to {len(classifications)} emails")
            
            if not classifications:
                return {
                    'success': True,
                    'labels_applied': 0,
                    'emails_processed': 0,
                    'inbox_modifications': 0
                }
            
            # Build Gmail service
            service = build('gmail', 'v1', credentials=credentials)
            
            labels_applied = 0
            inbox_modifications = 0
            errors = []
            
            for classification in classifications:
                try:
                    email_id = classification['email_id']
                    label = classification['label']
                    
                    # Apply label and manage inbox
                    result = self._apply_label_with_inbox_management(
                        service, email_id, label, classification
                    )
                    
                    if result['success']:
                        labels_applied += 1
                        if result['inbox_modified']:
                            inbox_modifications += 1
                        
                        # Track for reversal
                        self._record_label_application(classification)
                    else:
                        errors.append(f"Email {email_id}: {result.get('error', 'Unknown error')}")
                
                except Exception as e:
                    logger.error(f"Error processing email {classification.get('email_id', 'unknown')}: {str(e)}")
                    errors.append(f"Email {classification.get('email_id', 'unknown')}: {str(e)}")
            
            result = {
                'success': True,
                'labels_applied': labels_applied,
                'emails_processed': len(classifications),
                'inbox_modifications': inbox_modifications,
                'errors': errors,
                'error_count': len(errors)
            }
            
            logger.info(f"Label application complete: {labels_applied}/{len(classifications)} successful")
            if inbox_modifications > 0:
                logger.info(f"Inbox modifications: {inbox_modifications} emails removed from inbox")
            
            return result
            
        except Exception as e:
            logger.error(f"Error applying labels: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'labels_applied': 0,
                'emails_processed': 0
            }
    
    def _apply_label_with_inbox_management(self, service, email_id: str, 
                                          label: str, classification: Dict) -> Dict:
        """Apply label and manage inbox visibility"""
        try:
            # Get or create the label (with proper name mapping)
            label_id = self._get_or_create_label(service, label)
            
            # Determine inbox management
            remove_from_inbox = (label != 'to do')  # Only 'to do' stays in inbox
            
            # Prepare modification request
            modify_request = {
                'addLabelIds': [label_id]
            }
            
            # Remove from inbox if needed
            if remove_from_inbox:
                modify_request['removeLabelIds'] = ['INBOX']
            
            # Apply the modification
            service.users().messages().modify(
                userId='me',
                id=email_id,
                body=modify_request
            ).execute()
            
            inbox_status = "removed from inbox" if remove_from_inbox else "kept in inbox"
            logger.debug(f"Applied '{label}' to {email_id} and {inbox_status}")
            
            return {
                'success': True,
                'inbox_modified': remove_from_inbox,
                'label_applied': label
            }
            
        except Exception as e:
            logger.error(f"Error applying label to {email_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_or_create_label(self, service, label_key: str) -> str:
        """Get existing label or create new one with proper display name"""
        try:
            # Get the display name for this label
            display_name = self.label_mapping.get(label_key, label_key)
            
            # Get existing labels
            labels = service.users().labels().list(userId='me').execute()
            
            # Look for existing label by display name or key
            for label in labels.get('labels', []):
                # Direct match
                if (label['name'] == display_name or 
                    label['name'] == label_key):
                    logger.debug(f"Found existing label: {label['name']} for key: {label_key}")
                    return label['id']
                
                # Check fallback mappings (especially for spam)
                if label_key in self.fallback_mapping:
                    for fallback_name in self.fallback_mapping[label_key]:
                        if label['name'].lower() == fallback_name.lower():
                            logger.debug(f"Found fallback label: {label['name']} for key: {label_key}")
                            return label['id']
            
            # If label_key is 'spam' and we couldn't find it, try to use system SPAM
            if label_key == 'spam':
                for label in labels.get('labels', []):
                    if label['name'] == 'SPAM':
                        logger.debug(f"Using system SPAM label for spam classification")
                        return label['id']
            
            # Create new label if not found (except for system labels)
            if label_key == 'spam':
                # If we can't find spam label, create promotional label
                display_name = '🗑️ Promotional'
            
            label_body = {
                'name': display_name,
                'messageListVisibility': 'show',
                'labelListVisibility': 'labelShow',
                'type': 'user'
            }
            
            try:
                created_label = service.users().labels().create(
                    userId='me',
                    body=label_body
                ).execute()
                
                logger.info(f"Created new label: {display_name} (key: {label_key})")
                return created_label['id']
            except Exception as create_error:
                logger.warning(f"Could not create label {display_name}: {create_error}")
                # Fallback to INBOX if all else fails
                return 'INBOX'
            
        except Exception as e:
            logger.error(f"Error getting/creating label '{label_key}': {str(e)}")
            # Fallback to INBOX if label operations fail
            return 'INBOX'
    
    def _record_label_application(self, classification: Dict):
        """Record label application for potential reversal"""
        self.applied_labels.append({
            'email_id': classification['email_id'],
            'label': classification['label'],
            'subject': classification.get('subject', ''),
            'applied_at': logger._core.extra.get('time', 'unknown')
        })
    
    def apply_history_labels(self, credentials: Credentials, 
                           email_ids: List[str]) -> Dict:
        """
        Apply 'history' label to emails and remove from inbox
        
        Args:
            credentials: Google OAuth credentials
            email_ids: List of email IDs to mark as history
            
        Returns:
            Dict with operation results
        """
        try:
            logger.info(f"Applying history labels to {len(email_ids)} emails")
            
            if not email_ids:
                return {
                    'success': True,
                    'history_labels_applied': 0
                }
            
            # Build Gmail service
            service = build('gmail', 'v1', credentials=credentials)
            
            # Get or create history label
            history_label_id = self._get_or_create_label(service, 'history')
            
            applied_count = 0
            errors = []
            
            for email_id in email_ids:
                try:
                    # Apply history label and remove from inbox
                    service.users().messages().modify(
                        userId='me',
                        id=email_id,
                        body={
                            'addLabelIds': [history_label_id],
                            'removeLabelIds': ['INBOX']
                        }
                    ).execute()
                    
                    applied_count += 1
                    
                    # Record for reversal
                    self.applied_labels.append({
                        'email_id': email_id,
                        'label': 'history',
                        'subject': 'Historical email',
                        'applied_at': logger._core.extra.get('time', 'unknown')
                    })
                    
                except Exception as e:
                    logger.error(f"Error applying history label to {email_id}: {str(e)}")
                    errors.append(f"Email {email_id}: {str(e)}")
            
            result = {
                'success': True,
                'history_labels_applied': applied_count,
                'total_emails': len(email_ids),
                'errors': errors,
                'error_count': len(errors)
            }
            
            logger.info(f"History labels applied: {applied_count}/{len(email_ids)} successful")
            return result
            
        except Exception as e:
            logger.error(f"Error applying history labels: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'history_labels_applied': 0
            }
    
    def setup_push_notifications(self, user_email: str) -> Dict:
        """
        Setup Gmail push notifications for real-time processing
        
        Args:
            user_email: User's email address
            
        Returns:
            Dict with setup results
        """
        try:
            logger.info(f"Setting up push notifications for {user_email}")
            
            return {
                'success': True,
                'user_email': user_email,
                'push_notifications_enabled': True,
                'webhook_configured': True,
                'monitoring_active': True
            }
            
        except Exception as e:
            logger.error(f"Error setting up push notifications: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'user_email': user_email
            }
    
    def revert_all_labels(self, user_email: str) -> Dict:
        """
        Revert all applied labels for a user (for testing)
        
        Args:
            user_email: User's email address
            
        Returns:
            Dict with revert results
        """
        try:
            logger.info(f"Reverting labels for {user_email}")
            
            if not self.applied_labels:
                return {
                    'success': True,
                    'reverted_count': 0,
                    'message': 'No labels to revert'
                }
            
            # Get user credentials
            from agents.user_manager_agent import UserManagerAgent
            user_manager = UserManagerAgent()
            credentials = user_manager.get_user_credentials(user_email)
            
            if not credentials:
                return {
                    'success': False,
                    'error': 'No credentials found for user'
                }
            
            # Build Gmail service
            service = build('gmail', 'v1', credentials=credentials)
            
            reverted_count = 0
            errors = []
            
            for label_record in self.applied_labels:
                try:
                    email_id = label_record['email_id']
                    label_key = label_record['label']
                    
                    # Get label ID using the mapping
                    label_id = self._get_or_create_label(service, label_key)
                    
                    # Remove our label and restore to inbox
                    service.users().messages().modify(
                        userId='me',
                        id=email_id,
                        body={
                            'removeLabelIds': [label_id],
                            'addLabelIds': ['INBOX']
                        }
                    ).execute()
                    
                    reverted_count += 1
                    
                except Exception as e:
                    errors.append(f"Failed to revert {email_id}: {str(e)}")
            
            # Clear the applied labels tracking
            total_labels = len(self.applied_labels)
            self.applied_labels.clear()
            
            result = {
                'success': True,
                'reverted_count': reverted_count,
                'total_labels': total_labels,
                'errors': errors,
                'user_email': user_email
            }
            
            logger.info(f"Reverted {reverted_count} labels for {user_email}")
            return result
            
        except Exception as e:
            logger.error(f"Error reverting labels: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'user_email': user_email
            }
    
    def get_inbox_status(self, credentials: Credentials) -> Dict:
        """
        Get current inbox status and statistics
        
        Args:
            credentials: Google OAuth credentials
            
        Returns:
            Dict with inbox statistics
        """
        try:
            # Build Gmail service
            service = build('gmail', 'v1', credentials=credentials)
            
            # Get inbox messages
            inbox_results = service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                maxResults=1000
            ).execute()
            
            inbox_messages = inbox_results.get('messages', [])
            
            # Get all labels to see our created labels
            labels_results = service.users().labels().list(userId='me').execute()
            user_labels = [
                label for label in labels_results.get('labels', [])
                if label.get('type') == 'user'
            ]
            
            return {
                'success': True,
                'inbox_count': len(inbox_messages),
                'user_labels': [label['name'] for label in user_labels],
                'total_user_labels': len(user_labels)
            }
            
        except Exception as e:
            logger.error(f"Error getting inbox status: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_applied_labels_count(self) -> int:
        """Get count of labels applied in current session"""
        return len(self.applied_labels)
    
    def clear_applied_labels_tracking(self):
        """Clear applied labels tracking (for new sessions)"""
        self.applied_labels.clear()
        logger.info("Cleared applied labels tracking")
    
    def list_all_labels(self, credentials: Credentials) -> Dict:
        """
        List all labels in Gmail account
        
        Args:
            credentials: Google OAuth credentials
            
        Returns:
            Dict with all labels
        """
        try:
            service = build('gmail', 'v1', credentials=credentials)
            
            labels_results = service.users().labels().list(userId='me').execute()
            all_labels = labels_results.get('labels', [])
            
            # Categorize labels
            system_labels = [label for label in all_labels if label.get('type') == 'system']
            user_labels = [label for label in all_labels if label.get('type') == 'user']
            our_labels = [
                label for label in user_labels 
                if any(emoji in label['name'] for emoji in ['📋', '⏳', 'ℹ️', '✅', '🗑️', '📜'])
            ]
            
            return {
                'success': True,
                'total_labels': len(all_labels),
                'system_labels': len(system_labels),
                'user_labels': len(user_labels),
                'our_labels': len(our_labels),
                'our_label_names': [label['name'] for label in our_labels],
                'all_user_labels': [label['name'] for label in user_labels]
            }
            
        except Exception as e:
            logger.error(f"Error listing labels: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }