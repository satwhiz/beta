# workflows/user_onboarding_workflow.py - Fixed for Agno framework
from typing import Dict
from loguru import logger

class UserOnboardingWorkflow:
    """Workflow for onboarding new users to the email system"""
    
    def __init__(self):
        self.workflow_name = "User Onboarding"
    
    def onboard_user(self, user_email: str, user_manager, gmail_manager) -> Dict:
        """
        Complete user onboarding process
        
        Args:
            user_email: Email address of user to onboard
            user_manager: UserManagerAgent instance
            gmail_manager: GmailManagerAgent instance
            
        Returns:
            Dict with onboarding results
        """
        try:
            logger.info(f"Starting user onboarding workflow for {user_email}")
            
            # Step 1: Register user with OAuth
            logger.info("Step 1: User registration and authentication")
            registration_result = user_manager.register_user(user_email)
            
            if not registration_result['success']:
                return {
                    'success': False,
                    'error': f"Registration failed: {registration_result.get('error', 'Unknown error')}",
                    'user_email': user_email,
                    'step_failed': 'registration'
                }
            
            logger.info(f"✅ User {user_email} registered successfully")
            
            # Step 2: Setup Gmail access and verify permissions
            logger.info("Step 2: Gmail access verification")
            credentials = user_manager.get_user_credentials(user_email)
            
            if not credentials:
                return {
                    'success': False,
                    'error': 'Failed to retrieve user credentials',
                    'user_email': user_email,
                    'step_failed': 'credentials'
                }
            
            # Test Gmail access
            try:
                inbox_status = gmail_manager.get_inbox_status(credentials)
                
                if not inbox_status['success']:
                    return {
                        'success': False,
                        'error': f"Gmail access failed: {inbox_status.get('error', 'Unknown error')}",
                        'user_email': user_email,
                        'step_failed': 'gmail_access'
                    }
                
                logger.info(f"✅ Gmail access verified - {inbox_status['inbox_count']} emails in inbox")
            except Exception as e:
                return {
                    'success': False,
                    'error': f"Gmail verification failed: {str(e)}",
                    'user_email': user_email,
                    'step_failed': 'gmail_verification'
                }
            
            # Step 3: Setup monitoring (placeholder for push notifications)
            logger.info("Step 3: Setting up email monitoring")
            try:
                monitoring_result = gmail_manager.setup_push_notifications(user_email)
                
                if not monitoring_result['success']:
                    logger.warning(f"Monitoring setup failed: {monitoring_result.get('error', 'Unknown error')}")
                    # Don't fail onboarding for monitoring issues
                else:
                    user_manager.set_monitoring_active(user_email, True)
                    logger.info("✅ Email monitoring setup complete")
            except Exception as e:
                logger.warning(f"Monitoring setup failed: {str(e)}")
                monitoring_result = {'success': False, 'error': str(e)}
            
            # Step 4: Return success
            result = {
                'success': True,
                'user_email': user_email,
                'credentials_stored': True,
                'gmail_access_verified': True,
                'inbox_count': inbox_status.get('inbox_count', 0),
                'monitoring_setup': monitoring_result.get('success', False),
                'created_at': registration_result['created_at'],
                'next_steps': [
                    'Process existing emails',
                    'Start real-time monitoring',
                    'Begin email classification'
                ]
            }
            
            logger.info(f"✅ User onboarding completed for {user_email}")
            return result
            
        except Exception as e:
            logger.error(f"Error in user onboarding workflow: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'user_email': user_email,
                'step_failed': 'workflow_error'
            }
    
    def verify_user_setup(self, user_email: str, user_manager, gmail_manager) -> Dict:
        """
        Verify user setup is complete and working
        
        Args:
            user_email: Email address to verify
            user_manager: UserManagerAgent instance
            gmail_manager: GmailManagerAgent instance
            
        Returns:
            Dict with verification results
        """
        try:
            logger.info(f"Verifying user setup for {user_email}")
            
            # Check user exists
            user_info = user_manager.get_user_info(user_email)
            if not user_info['exists']:
                return {
                    'verified': False,
                    'error': 'User not found in database',
                    'user_email': user_email
                }
            
            # Check credentials
            credentials = user_manager.get_user_credentials(user_email)
            if not credentials:
                return {
                    'verified': False,
                    'error': 'No valid credentials found',
                    'user_email': user_email
                }
            
            # Test Gmail access
            try:
                inbox_status = gmail_manager.get_inbox_status(credentials)
                if not inbox_status['success']:
                    return {
                        'verified': False,
                        'error': f"Gmail access failed: {inbox_status.get('error')}",
                        'user_email': user_email
                    }
            except Exception as e:
                return {
                    'verified': False,
                    'error': f"Gmail verification failed: {str(e)}",
                    'user_email': user_email
                }
            
            verification_result = {
                'verified': True,
                'user_email': user_email,
                'user_info': user_info,
                'gmail_accessible': True,
                'inbox_count': inbox_status.get('inbox_count', 0),
                'user_labels': inbox_status.get('user_labels', []),
                'ready_for_processing': True
            }
            
            logger.info(f"✅ User setup verified for {user_email}")
            return verification_result
            
        except Exception as e:
            logger.error(f"Error verifying user setup: {str(e)}")
            return {
                'verified': False,
                'error': str(e),
                'user_email': user_email
            }