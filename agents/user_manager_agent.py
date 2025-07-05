# agents/user_manager_agent.py
import csv
import os
import hashlib
from datetime import datetime
from typing import Dict, Optional
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from loguru import logger

class UserManagerAgent(Agent):
    """Agent responsible for user registration, authentication, and data management"""
    
    def __init__(self):
        super().__init__(
            name="User Manager Agent",
            role="Manage user registration, authentication, and credential storage",
            model=OpenAIChat(id="gpt-4o"),
            instructions=[
                "You are responsible for user management in the email system",
                "Handle user registration with OAuth authentication",
                "Store user credentials securely in CSV format", 
                "Manage user data and processing history",
                "Ensure data privacy and security"
            ]
        )
        
        self.users_csv = "users.csv"
        self.gmail_scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify'
        ]
        self._ensure_csv_exists()
    
    def _ensure_csv_exists(self):
        """Create users CSV file if it doesn't exist"""
        if not os.path.exists(self.users_csv):
            with open(self.users_csv, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    'user_email', 'access_token_hash', 'refresh_token_hash',
                    'created_at', 'last_processed_at', 'total_emails_processed',
                    'labels_applied', 'monitoring_active'
                ])
            logger.info(f"Created users database: {self.users_csv}")
    
    def register_user(self, user_email: str) -> Dict:
        """
        Register a new user with OAuth authentication
        
        Args:
            user_email: Email address to register
            
        Returns:
            Dict with registration results
        """
        try:
            logger.info(f"Starting user registration for {user_email}")
            
            # Check if user already exists
            if self.user_exists(user_email):
                return {
                    'success': False,
                    'error': 'User already registered',
                    'user_email': user_email
                }
            
            # Start OAuth flow
            credentials = self._authenticate_user(user_email)
            if not credentials:
                return {
                    'success': False,
                    'error': 'OAuth authentication failed',
                    'user_email': user_email
                }
            
            # Store user data
            success = self._store_user_data(user_email, credentials)
            if not success:
                return {
                    'success': False,
                    'error': 'Failed to store user data',
                    'user_email': user_email
                }
            
            logger.info(f"User {user_email} registered successfully")
            return {
                'success': True,
                'user_email': user_email,
                'credentials_stored': True,
                'created_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error registering user {user_email}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'user_email': user_email
            }
    
    def _authenticate_user(self, user_email: str) -> Optional[Credentials]:
        """Perform OAuth authentication for user"""
        try:
            logger.info(f"Starting OAuth authentication for {user_email}")
            
            if not os.path.exists('credentials.json'):
                logger.error("credentials.json not found")
                return None
            
            # Create OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', 
                self.gmail_scopes
            )
            
            print(f"\n🔐 Starting OAuth for {user_email}")
            print("This will open a browser window for Google sign-in...")
            print(f"Please sign in with: {user_email}")
            
            input("Press Enter to continue...")
            
            # Run OAuth flow
            credentials = flow.run_local_server(
                port=0,  # Use any available port
                access_type='offline'
            )
            
            logger.info(f"OAuth authentication successful for {user_email}")
            return credentials
            
        except Exception as e:
            logger.error(f"OAuth authentication failed for {user_email}: {str(e)}")
            return None
    
    def _store_user_data(self, user_email: str, credentials: Credentials) -> bool:
        """Store user data and credentials securely"""
        try:
            # Hash tokens for security (in production, use proper encryption)
            access_hash = hashlib.sha256(credentials.token.encode()).hexdigest()[:32]
            refresh_hash = hashlib.sha256(
                (credentials.refresh_token or '').encode()
            ).hexdigest()[:32]
            
            # Append to CSV
            with open(self.users_csv, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    user_email,
                    access_hash,
                    refresh_hash,
                    datetime.now().isoformat(),
                    '',  # last_processed_at
                    0,   # total_emails_processed
                    0,   # labels_applied
                    False  # monitoring_active
                ])
            
            # Store full credentials temporarily (in production, use secure storage)
            self._store_credentials_temp(user_email, credentials)
            
            logger.info(f"User data stored for {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing user data: {str(e)}")
            return False
    
    def _store_credentials_temp(self, user_email: str, credentials: Credentials):
        """Store credentials temporarily for session use"""
        # In production, use secure credential storage
        # For now, store in memory or temp file
        cred_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        # Store in temp file (in production, use secure storage)
        import json
        os.makedirs('temp_credentials', exist_ok=True)
        safe_email = user_email.replace('@', '_at_').replace('.', '_dot_')
        
        with open(f'temp_credentials/{safe_email}_creds.json', 'w') as f:
            json.dump(cred_data, f)
        
        logger.info(f"Temporary credentials stored for {user_email}")
    
    def get_user_credentials(self, user_email: str) -> Optional[Credentials]:
        """Get stored credentials for a user"""
        try:
            safe_email = user_email.replace('@', '_at_').replace('.', '_dot_')
            cred_file = f'temp_credentials/{safe_email}_creds.json'
            
            if not os.path.exists(cred_file):
                logger.warning(f"No credentials found for {user_email}")
                return None
            
            import json
            with open(cred_file, 'r') as f:
                cred_data = json.load(f)
            
            credentials = Credentials(
                token=cred_data['token'],
                refresh_token=cred_data.get('refresh_token'),
                token_uri=cred_data['token_uri'],
                client_id=cred_data['client_id'],
                client_secret=cred_data['client_secret'],
                scopes=cred_data['scopes']
            )
            
            return credentials
            
        except Exception as e:
            logger.error(f"Error getting credentials for {user_email}: {str(e)}")
            return None
    
    def user_exists(self, user_email: str) -> bool:
        """Check if user exists in database"""
        try:
            with open(self.users_csv, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row['user_email'] == user_email:
                        return True
            return False
        except Exception as e:
            logger.error(f"Error checking user existence: {str(e)}")
            return False
    
    def get_user_info(self, user_email: str) -> Dict:
        """Get user information from database"""
        try:
            with open(self.users_csv, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row['user_email'] == user_email:
                        return {
                            'exists': True,
                            'email': row['user_email'],
                            'created_at': row['created_at'],
                            'last_processed_at': row['last_processed_at'],
                            'total_emails_processed': int(row['total_emails_processed']),
                            'labels_applied': int(row['labels_applied']),
                            'monitoring_active': row['monitoring_active'].lower() == 'true'
                        }
            
            return {'exists': False}
            
        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
            return {'exists': False, 'error': str(e)}
    
    def update_user_stats(self, user_email: str, emails_processed: int = 0, 
                         labels_applied: int = 0) -> bool:
        """Update user processing statistics"""
        try:
            # Read all rows
            rows = []
            with open(self.users_csv, 'r') as file:
                reader = csv.DictReader(file)
                rows = list(reader)
            
            # Update the specific user
            for row in rows:
                if row['user_email'] == user_email:
                    row['last_processed_at'] = datetime.now().isoformat()
                    row['total_emails_processed'] = str(
                        int(row['total_emails_processed']) + emails_processed
                    )
                    row['labels_applied'] = str(
                        int(row['labels_applied']) + labels_applied
                    )
                    break
            
            # Write back
            with open(self.users_csv, 'w', newline='') as file:
                fieldnames = [
                    'user_email', 'access_token_hash', 'refresh_token_hash',
                    'created_at', 'last_processed_at', 'total_emails_processed',
                    'labels_applied', 'monitoring_active'
                ]
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            
            logger.info(f"Updated stats for {user_email}: +{emails_processed} emails, +{labels_applied} labels")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user stats: {str(e)}")
            return False
    
    def set_monitoring_active(self, user_email: str, active: bool) -> bool:
        """Set monitoring status for user"""
        try:
            # Read all rows
            rows = []
            with open(self.users_csv, 'r') as file:
                reader = csv.DictReader(file)
                rows = list(reader)
            
            # Update the specific user
            for row in rows:
                if row['user_email'] == user_email:
                    row['monitoring_active'] = str(active)
                    break
            
            # Write back
            with open(self.users_csv, 'w', newline='') as file:
                fieldnames = [
                    'user_email', 'access_token_hash', 'refresh_token_hash',
                    'created_at', 'last_processed_at', 'total_emails_processed',
                    'labels_applied', 'monitoring_active'
                ]
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            
            logger.info(f"Set monitoring active={active} for {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting monitoring status: {str(e)}")
            return False
    
    def clear_processing_history(self, user_email: str) -> bool:
        """Clear processing history for user (for testing)"""
        try:
            # Reset stats to zero
            rows = []
            with open(self.users_csv, 'r') as file:
                reader = csv.DictReader(file)
                rows = list(reader)
            
            for row in rows:
                if row['user_email'] == user_email:
                    row['total_emails_processed'] = '0'
                    row['labels_applied'] = '0'
                    row['last_processed_at'] = ''
                    break
            
            # Write back
            with open(self.users_csv, 'w', newline='') as file:
                fieldnames = [
                    'user_email', 'access_token_hash', 'refresh_token_hash',
                    'created_at', 'last_processed_at', 'total_emails_processed',
                    'labels_applied', 'monitoring_active'
                ]
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            
            logger.info(f"Cleared processing history for {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing processing history: {str(e)}")
            return False