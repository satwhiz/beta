# tools/gmail_tools.py
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from typing import List, Dict, Optional
import base64
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from models.email_models import EmailMessage, EmailThread
from datetime import datetime
from email.utils import parsedate_to_datetime
import re

# Use print statements as fallback if loguru is not available
try:
    from loguru import logger
except ImportError:
    class SimpleLogger:
        def error(self, msg): print(f"❌ ERROR: {msg}")
        def info(self, msg): print(f"ℹ️  INFO: {msg}")
        def warning(self, msg): print(f"⚠️  WARNING: {msg}")
    logger = SimpleLogger()

# Simple date utils class to replace missing dependency
class DateUtils:
    @staticmethod
    def parse_gmail_date(date_str: str) -> datetime:
        """Parse Gmail date string to datetime"""
        try:
            return parsedate_to_datetime(date_str)
        except:
            return datetime.now()

class GmailTools:
    def __init__(self, credentials: Credentials):
        self.service = build('gmail', 'v1', credentials=credentials)
        self.date_utils = DateUtils()
        print("✅ Gmail Tools initialized")
    
    def fetch_emails(self, limit: int = 100, query: str = "") -> List[EmailMessage]:
        """Fetch emails from Gmail"""
        try:
            results = self.service.users().messages().list(
                userId='me',
                maxResults=limit,
                q=query
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                email_data = self.service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()
                
                email_obj = self._parse_email_message(email_data)
                if email_obj:
                    emails.append(email_obj)
            
            print(f"📧 Fetched {len(emails)} emails")
            return emails
        except Exception as e:
            logger.error(f"Error fetching emails: {str(e)}")
            return []
    
    def get_thread_messages(self, thread_id: str) -> List[EmailMessage]:
        """Get all messages in a thread"""
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id
            ).execute()
            
            messages = []
            for message in thread['messages']:
                email_obj = self._parse_email_message(message)
                if email_obj:
                    messages.append(email_obj)
            
            print(f"📧 Retrieved {len(messages)} messages from thread {thread_id}")
            return messages
        except Exception as e:
            logger.error(f"Error fetching thread messages: {str(e)}")
            return []
    
    def apply_label(self, message_id: str, label: str) -> bool:
        """Apply a label to an email"""
        try:
            # First, get or create the label
            label_id = self._get_or_create_label(label)
            
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            
            print(f"✅ Applied label '{label}' to message {message_id}")
            return True
        except Exception as e:
            logger.error(f"Error applying label: {str(e)}")
            return False
    
    def create_draft(self, to_emails: List[str], subject: str, content: str,
                    cc_emails: Optional[List[str]] = None,
                    bcc_emails: Optional[List[str]] = None) -> Optional[str]:
        """Create a draft email"""
        try:
            message = MIMEMultipart()
            message['to'] = ', '.join(to_emails)
            message['subject'] = subject
            
            if cc_emails:
                message['cc'] = ', '.join(cc_emails)
            if bcc_emails:
                message['bcc'] = ', '.join(bcc_emails)
            
            message.attach(MIMEText(content, 'plain'))
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            draft = self.service.users().drafts().create(
                userId='me',
                body={'message': {'raw': raw_message}}
            ).execute()
            
            print(f"✅ Created draft with ID: {draft['id']}")
            return draft['id']
        except Exception as e:
            logger.error(f"Error creating draft: {str(e)}")
            return None
    
    def _parse_email_message(self, message_data: Dict) -> Optional[EmailMessage]:
        """Parse Gmail message data into EmailMessage object"""
        try:
            headers = message_data['payload']['headers']
            header_dict = {h['name']: h['value'] for h in headers}
            
            # Extract email content
            content = self._extract_email_content(message_data['payload'])
            
            # Parse date
            date_str = header_dict.get('Date', '')
            date = self.date_utils.parse_gmail_date(date_str)
            
            return EmailMessage(
                id=message_data['id'],
                thread_id=message_data['threadId'],
                from_email=header_dict.get('From', ''),
                to_emails=self._parse_email_addresses(header_dict.get('To', '')),
                cc_emails=self._parse_email_addresses(header_dict.get('Cc', '')),
                bcc_emails=self._parse_email_addresses(header_dict.get('Bcc', '')),
                subject=header_dict.get('Subject', ''),
                content=content,
                date=date,
                labels=message_data.get('labelIds', [])
            )
        except Exception as e:
            logger.error(f"Error parsing email message: {str(e)}")
            return None
    
    def _extract_email_content(self, payload: Dict) -> str:
        """Extract text content from email payload"""
        content = ""
        
        try:
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                        data = part['body']['data']
                        content = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
                    elif part['mimeType'] == 'text/html' and 'data' in part['body'] and not content:
                        # Fallback to HTML if no plain text
                        data = part['body']['data']
                        html_content = base64.urlsafe_b64decode(data).decode('utf-8')
                        content = self._html_to_text(html_content)
            elif payload['mimeType'] == 'text/plain' and 'data' in payload['body']:
                data = payload['body']['data']
                content = base64.urlsafe_b64decode(data).decode('utf-8')
            elif payload['mimeType'] == 'text/html' and 'data' in payload['body']:
                data = payload['body']['data']
                html_content = base64.urlsafe_b64decode(data).decode('utf-8')
                content = self._html_to_text(html_content)
        except Exception as e:
            logger.error(f"Error extracting email content: {str(e)}")
        
        return content[:2000]  # Limit content length
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML to plain text (simple version)"""
        try:
            # Remove HTML tags
            clean = re.compile('<.*?>')
            text = re.sub(clean, '', html_content)
            
            # Decode HTML entities
            import html
            text = html.unescape(text)
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
            
        except Exception as e:
            logger.error(f"Error converting HTML to text: {str(e)}")
            return html_content
    
    def _parse_email_addresses(self, address_string: str) -> List[str]:
        """Parse comma-separated email addresses"""
        if not address_string:
            return []
        
        # Extract email addresses using regex to handle complex formats
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', address_string)
        return emails if emails else [addr.strip() for addr in address_string.split(',')]
    
    def _get_or_create_label(self, label_name: str) -> str:
        """Get existing label or create new one"""
        try:
            # Get existing labels
            labels = self.service.users().labels().list(userId='me').execute()
            
            for label in labels.get('labels', []):
                if label['name'] == label_name:
                    return label['id']
            
            # Create new label if not found
            label_body = {
                'name': label_name,
                'messageListVisibility': 'show',
                'labelListVisibility': 'labelShow'
            }
            
            created_label = self.service.users().labels().create(
                userId='me',
                body=label_body
            ).execute()
            
            print(f"✅ Created new label: {label_name}")
            return created_label['id']
        except Exception as e:
            logger.error(f"Error getting/creating label: {str(e)}")
            return 'INBOX'  # Fallback to inbox
    
    def get_labels(self) -> List[Dict]:
        """Get all labels"""
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            return [{'id': label['id'], 'name': label['name']} for label in labels]
            
        except Exception as e:
            logger.error(f"Error getting labels: {str(e)}")
            return []
    
    def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={
                    'removeLabelIds': ['UNREAD']
                }
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error marking as read: {str(e)}")
            return False
    
    def get_profile(self) -> Dict:
        """Get Gmail profile information"""
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return {
                'email': profile.get('emailAddress'),
                'total_messages': profile.get('messagesTotal'),
                'total_threads': profile.get('threadsTotal')
            }
            
        except Exception as e:
            logger.error(f"Error getting profile: {str(e)}")
            return {}