from datetime import datetime, timedelta
from typing import Optional
import pytz

class DateUtils:
    @staticmethod
    def is_older_than_days(date: datetime, days: int) -> bool:
        """Check if date is older than specified days"""
        threshold = datetime.now(pytz.UTC) - timedelta(days=days)
        if date.tzinfo is None:
            date = pytz.UTC.localize(date)
        return date < threshold
    
    @staticmethod
    def get_days_ago(days: int) -> datetime:
        """Get datetime object for N days ago"""
        return datetime.now(pytz.UTC) - timedelta(days=days)
    
    @staticmethod
    def format_for_gmail_query(date: datetime) -> str:
        """Format date for Gmail API query"""
        return date.strftime("%Y/%m/%d")
    
    @staticmethod
    def parse_gmail_date(date_str: str) -> datetime:
        """Parse Gmail date string to datetime"""
        try:
            return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
        except ValueError:
            # Try alternative format
            return datetime.strptime(date_str, "%d %b %Y %H:%M:%S %z")
