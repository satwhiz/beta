# agents/history_checker_agent.py
from typing import Dict, List
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from models.email_models import EmailMessage
from datetime import datetime, timedelta
from loguru import logger

class HistoryCheckerAgent(Agent):
    """Agent responsible for checking email age and applying 7-day rule"""
    
    def __init__(self):
        super().__init__(
            name="History Checker Agent",
            role="Apply 7-day rule and manage email history classification",
            model=OpenAIChat(id="gpt-4o"),
            instructions=[
                "You are responsible for implementing the 7-day rule",
                "Emails older than 7 days automatically get 'history' label",
                "Check email dates and determine if they need history classification",
                "Provide clear reasoning for history classification decisions",
                "Handle timezone differences and date parsing accurately"
            ]
        )
        
        self.history_threshold_days = 7
    
    def check_email_age(self, email: EmailMessage) -> Dict:
        """
        Check if email should be classified as history based on age
        
        Args:
            email: EmailMessage object to check
            
        Returns:
            Dict with age check results
        """
        try:
            # Calculate age
            now = datetime.now()
            email_date = email.date.replace(tzinfo=None) if email.date.tzinfo else email.date
            age_delta = now - email_date
            days_old = age_delta.days
            
            # Check against threshold
            is_history = days_old >= self.history_threshold_days
            
            result = {
                'email_id': email.id,
                'subject': email.subject,
                'email_date': email.date.isoformat(),
                'days_old': days_old,
                'is_history': is_history,
                'threshold_days': self.history_threshold_days,
                'reasoning': self._get_age_reasoning(days_old, is_history)
            }
            
            if is_history:
                logger.info(f"Email {email.id} is {days_old} days old - marking as history")
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking email age: {str(e)}")
            return {
                'email_id': email.id,
                'is_history': False,
                'error': str(e)
            }
    
    def check_multiple_emails(self, emails: List[EmailMessage]) -> Dict:
        """
        Check age for multiple emails
        
        Args:
            emails: List of EmailMessage objects
            
        Returns:
            Dict with results for all emails
        """
        try:
            logger.info(f"Checking age for {len(emails)} emails")
            
            history_emails = []
            recent_emails = []
            age_results = []
            
            for email in emails:
                age_result = self.check_email_age(email)
                age_results.append(age_result)
                
                if age_result['is_history']:
                    history_emails.append(email)
                else:
                    recent_emails.append(email)
            
            result = {
                'total_emails': len(emails),
                'history_emails': len(history_emails),
                'recent_emails': len(recent_emails),
                'history_email_ids': [e.id for e in history_emails],
                'recent_email_ids': [e.id for e in recent_emails],
                'age_results': age_results,
                'threshold_days': self.history_threshold_days
            }
            
            logger.info(f"Age check complete: {len(history_emails)} history, {len(recent_emails)} recent")
            return result
            
        except Exception as e:
            logger.error(f"Error checking multiple email ages: {str(e)}")
            return {
                'total_emails': len(emails),
                'error': str(e)
            }
    
    def _get_age_reasoning(self, days_old: int, is_history: bool) -> str:
        """Generate reasoning for age classification"""
        if is_history:
            return f"Email is {days_old} days old, which exceeds the {self.history_threshold_days}-day threshold. Automatically classified as 'history'."
        else:
            return f"Email is {days_old} days old, which is within the {self.history_threshold_days}-day threshold. Eligible for AI classification."
    
    def get_history_emails(self, emails: List[EmailMessage]) -> List[EmailMessage]:
        """Get only emails that should be classified as history"""
        try:
            history_emails = []
            
            for email in emails:
                age_result = self.check_email_age(email)
                if age_result['is_history']:
                    history_emails.append(email)
            
            return history_emails
            
        except Exception as e:
            logger.error(f"Error getting history emails: {str(e)}")
            return []
    
    def get_recent_emails(self, emails: List[EmailMessage]) -> List[EmailMessage]:
        """Get only emails that are recent (not history)"""
        try:
            recent_emails = []
            
            for email in emails:
                age_result = self.check_email_age(email)
                if not age_result['is_history']:
                    recent_emails.append(email)
            
            return recent_emails
            
        except Exception as e:
            logger.error(f"Error getting recent emails: {str(e)}")
            return []
    
    def set_history_threshold(self, days: int):
        """Set custom history threshold (default is 7 days)"""
        self.history_threshold_days = days
        logger.info(f"History threshold set to {days} days")
    
    def get_age_statistics(self, emails: List[EmailMessage]) -> Dict:
        """Get age distribution statistics for emails"""
        try:
            age_stats = {
                'total_emails': len(emails),
                'age_distribution': {
                    '0-1 days': 0,
                    '2-3 days': 0,
                    '4-7 days': 0,
                    '8-14 days': 0,
                    '15-30 days': 0,
                    '30+ days': 0
                },
                'average_age_days': 0,
                'oldest_email_days': 0,
                'newest_email_days': 0
            }
            
            if not emails:
                return age_stats
            
            ages = []
            now = datetime.now()
            
            for email in emails:
                email_date = email.date.replace(tzinfo=None) if email.date.tzinfo else email.date
                days_old = (now - email_date).days
                ages.append(days_old)
                
                # Categorize age
                if days_old <= 1:
                    age_stats['age_distribution']['0-1 days'] += 1
                elif days_old <= 3:
                    age_stats['age_distribution']['2-3 days'] += 1
                elif days_old <= 7:
                    age_stats['age_distribution']['4-7 days'] += 1
                elif days_old <= 14:
                    age_stats['age_distribution']['8-14 days'] += 1
                elif days_old <= 30:
                    age_stats['age_distribution']['15-30 days'] += 1
                else:
                    age_stats['age_distribution']['30+ days'] += 1
            
            age_stats['average_age_days'] = sum(ages) / len(ages)
            age_stats['oldest_email_days'] = max(ages)
            age_stats['newest_email_days'] = min(ages)
            
            return age_stats
            
        except Exception as e:
            logger.error(f"Error calculating age statistics: {str(e)}")
            return {'error': str(e)}