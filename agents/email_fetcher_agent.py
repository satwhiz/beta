# agents/email_fetcher_agent.py
from typing import Dict, List, Optional
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from models.email_models import EmailMessage
from datetime import datetime
import base64
import re
from loguru import logger

class EmailFetcherAgent(Agent):
    """Agent responsible for fetching emails from Gmail"""
    
    def __init__(self):
        super().__init__(
            name="Email Fetcher Agent",
            role="Fetch and parse emails from Gmail API",
            model=OpenAIChat(id="gpt-4o"),
            instructions=[
                "You are responsible for fetching emails from Gmail",
                "Parse email data into structured EmailMessage objects",
                "Handle different email formats and content types",
                "Manage Gmail API interactions efficiently",
                "Provide detailed email metadata and content"
            ]
        )
    
    def fetch_emails(self, credentials: Credentials, limit: int = 100, 
                    query: str = "") -> List[EmailMessage]:
        """
        Fetch emails from Gmail
        
        Args:
            credentials: Google OAuth credentials
            limit: Maximum number of emails to fetch
            query: Gmail search query (optional)
            
        Returns:
            List of EmailMessage objects
        """
        try:
            logger.info(f"Fetching emails (limit: {limit}, query: '{query}')")
            
            # Build Gmail service
            service = build('gmail', 'v1', credentials=credentials)
            
            # Get message list
            results = service.users().messages().list(
                userId='me',
                maxResults=limit,
                q=query
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            logger.info(f"Found {len(messages)} messages, parsing...")
            
            for i, message in enumerate(messages):
                try:
                    # Get full message
                    msg = service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='full'
                    ).execute()
                    
                    # Parse email
                    email_obj = self._parse_email_message(msg)
                    if email_obj:
                        emails.append(email_obj)
                    
                    # Progress indicator
                    if (i + 1) % 10 == 0:
                        logger.info(f"Parsed {i + 1}/{len(messages)} emails")
                        
                except Exception as e:
                    logger.error(f"Error parsing email {message['id']}: {str(e)}")
                    continue
            
            logger.info(f"Successfully fetched {len(emails)} emails")
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching emails: {str(e)}")
            return []
    
    def fetch_single_email(self, credentials: Credentials, message_id: str) -> Optional[EmailMessage]:
        """
        Fetch a single email by message ID
        
        Args:
            credentials: Google OAuth credentials
            message_id: Gmail message ID
            
        Returns:
            EmailMessage object or None
        """
        try:
            logger.info(f"Fetching single email: {message_id}")
            
            # Build Gmail service
            service = build('gmail', 'v1', credentials=credentials)
            
            # Get message
            msg = service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Parse email
            email_obj = self._parse_email_message(msg)
            
            if email_obj:
                logger.info(f"Successfully fetched email: {email_obj.subject}")
            
            return email_obj
            
        except Exception as e:
            logger.error(f"Error fetching email {message_id}: {str(e)}")
            return None
    
    def fetch_thread_emails(self, credentials: Credentials, thread_id: str) -> List[EmailMessage]:
        """
        Fetch all emails in a thread
        
        Args:
            credentials: Google OAuth credentials
            thread_id: Gmail thread ID
            
        Returns:
            List of EmailMessage objects in the thread
        """
        try:
            logger.info(f"Fetching thread emails: {thread_id}")
            
            # Build Gmail service
            service = build('gmail', 'v1', credentials=credentials)
            
            # Get thread
            thread = service.users().threads().get(
                userId='me',
                id=thread_id
            ).execute()
            
            emails = []
            for message in thread['messages']:
                email_obj = self._parse_email_message(message)
                if email_obj:
                    emails.append(email_obj)
            
            logger.info(f"Fetched {len(emails)} emails from thread {thread_id}")
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching thread {thread_id}: {str(e)}")
            return []
    
    def _parse_email_message(self, message_data: Dict) -> Optional[EmailMessage]:
        """Parse Gmail message data into EmailMessage object"""
        try:
            headers = message_data['payload']['headers']
            header_dict = {h['name']: h['value'] for h in headers}
            
            # Extract email content
            content = self._extract_email_content(message_data['payload'])
            
            # Parse date
            date_str = header_dict.get('Date', '')
            date = self._parse_date(date_str)
            
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
        """Convert HTML to plain text"""
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
        
        # Extract email addresses using regex
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', address_string)
        return emails if emails else [addr.strip() for addr in address_string.split(',')]
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse Gmail date string to datetime"""
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except:
            return datetime.now()
    
    def get_inbox_emails(self, credentials: Credentials, limit: int = 100) -> List[EmailMessage]:
        """Get emails from inbox only"""
        return self.fetch_emails(credentials, limit, query="in:inbox")
    
    def get_recent_emails(self, credentials: Credentials, days: int = 7, 
                         limit: int = 100) -> List[EmailMessage]:
        """Get emails from last N days"""
        query = f"newer_than:{days}d"
        return self.fetch_emails(credentials, limit, query=query)
    
    def get_old_emails(self, credentials: Credentials, days: int = 7, 
                      limit: int = 100) -> List[EmailMessage]:
        """Get emails older than N days"""
        query = f"older_than:{days}d"
        return self.fetch_emails(credentials, limit, query=query)