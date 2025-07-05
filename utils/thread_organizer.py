# utils/thread_organizer.py - Organize emails by threads
from typing import Dict, List
from models.email_models import EmailMessage
from models.response_models import ThreadInfo
from datetime import datetime

class ThreadOrganizer:
    def __init__(self):
        pass
    
    def organize_emails_by_thread(self, emails: List[EmailMessage]) -> Dict[str, List[EmailMessage]]:
        """
        Group emails by thread ID
        
        Args:
            emails: List of EmailMessage objects
            
        Returns:
            Dict mapping thread_id to list of emails in that thread
        """
        threads = {}
        
        for email in emails:
            thread_id = email.thread_id
            
            if thread_id not in threads:
                threads[thread_id] = []
            
            threads[thread_id].append(email)
        
        # Sort emails within each thread by date
        for thread_id in threads:
            threads[thread_id].sort(key=lambda x: x.date)
        
        return threads
    
    def get_thread_info(self, threads: Dict[str, List[EmailMessage]]) -> List[ThreadInfo]:
        """
        Generate thread information for each thread
        
        Args:
            threads: Dict mapping thread_id to emails
            
        Returns:
            List of ThreadInfo objects
        """
        thread_infos = []
        
        for thread_id, emails in threads.items():
            if not emails:
                continue
                
            # Sort emails by date
            sorted_emails = sorted(emails, key=lambda x: x.date)
            
            # Get all unique participants
            participants = set()
            for email in emails:
                participants.add(email.from_email)
                participants.update(email.to_emails)
                if email.cc_emails:
                    participants.update(email.cc_emails)
            
            # Get thread subject (from first email, removing Re:, Fwd: etc.)
            subject = sorted_emails[0].subject
            subject = self._clean_subject(subject)
            
            thread_info = ThreadInfo(
                thread_id=thread_id,
                emails=sorted_emails,
                participants=list(participants),
                subject=subject,
                start_date=sorted_emails[0].date.isoformat(),
                last_activity=sorted_emails[-1].date.isoformat(),
                email_count=len(emails)
            )
            
            thread_infos.append(thread_info)
        
        # Sort thread infos by last activity (most recent first)
        thread_infos.sort(key=lambda x: x.last_activity, reverse=True)
        
        return thread_infos
    
    def _clean_subject(self, subject: str) -> str:
        """Clean email subject by removing Re:, Fwd:, etc."""
        import re
        
        # Remove common prefixes
        cleaned = re.sub(r'^(Re:|RE:|Fwd:|FWD:|Fw:|FW:)\s*', '', subject, flags=re.IGNORECASE)
        
        # Remove multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def filter_threads_by_criteria(self, threads: Dict[str, List[EmailMessage]], 
                                 min_emails: int = 1, 
                                 max_emails: int = None,
                                 days_old: int = None) -> Dict[str, List[EmailMessage]]:
        """
        Filter threads based on various criteria
        
        Args:
            threads: Dict of threads
            min_emails: Minimum number of emails in thread
            max_emails: Maximum number of emails in thread  
            days_old: Only include threads with activity within N days
            
        Returns:
            Filtered dict of threads
        """
        filtered_threads = {}
        
        for thread_id, emails in threads.items():
            # Check email count criteria
            email_count = len(emails)
            if email_count < min_emails:
                continue
            if max_emails and email_count > max_emails:
                continue
            
            # Check age criteria
            if days_old:
                latest_email = max(emails, key=lambda x: x.date)
                days_since = (datetime.now() - latest_email.date).days
                if days_since > days_old:
                    continue
            
            filtered_threads[thread_id] = emails
        
        return filtered_threads
    
    def get_thread_statistics(self, threads: Dict[str, List[EmailMessage]]) -> Dict:
        """Get statistics about the threads"""
        if not threads:
            return {
                'total_threads': 0,
                'total_emails': 0,
                'avg_emails_per_thread': 0,
                'single_email_threads': 0,
                'multi_email_threads': 0,
                'longest_thread': 0
            }
        
        thread_sizes = [len(emails) for emails in threads.values()]
        total_emails = sum(thread_sizes)
        
        return {
            'total_threads': len(threads),
            'total_emails': total_emails,
            'avg_emails_per_thread': round(total_emails / len(threads), 1),
            'single_email_threads': sum(1 for size in thread_sizes if size == 1),
            'multi_email_threads': sum(1 for size in thread_sizes if size > 1),
            'longest_thread': max(thread_sizes),
            'thread_size_distribution': {
                '1 email': sum(1 for size in thread_sizes if size == 1),
                '2-3 emails': sum(1 for size in thread_sizes if 2 <= size <= 3),
                '4-5 emails': sum(1 for size in thread_sizes if 4 <= size <= 5),
                '6+ emails': sum(1 for size in thread_sizes if size >= 6)
            }
        }