# tools/text_processing.py - Minimal version for label generation only
import re
from typing import List

class TextProcessing:
    def __init__(self):
        pass
    
    def clean_email_content(self, content: str) -> str:
        """Clean email content by removing quotes, signatures, etc."""
        if not content:
            return ""
        
        # Remove email signatures (lines starting with --)
        content = re.sub(r'^--\s*$.*', '', content, flags=re.MULTILINE | re.DOTALL)
        
        # Remove quoted text (lines starting with >)
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            # Skip quoted lines
            if not line.strip().startswith('>'):
                cleaned_lines.append(line)
        
        content = '\n'.join(cleaned_lines)
        
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = content.strip()
        
        return content
    
    def summarize_text(self, text: str, max_sentences: int = 3) -> str:
        """Create a simple summary of the text"""
        if not text:
            return ""
        
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= max_sentences:
            return text
        
        # Simple extractive summarization - take first and last sentences
        if max_sentences == 1:
            return sentences[0] + "."
        elif max_sentences == 2:
            return sentences[0] + ". " + sentences[-1] + "."
        else:
            # Take first, middle, and last sentences
            middle_idx = len(sentences) // 2
            return sentences[0] + ". " + sentences[middle_idx] + ". " + sentences[-1] + "."
    
    def detect_meeting_request(self, content: str) -> bool:
        """Detect if email contains meeting request"""
        if not content:
            return False
        
        meeting_keywords = [
            'meeting', 'call', 'conference', 'appointment', 'schedule',
            'calendar', 'zoom', 'teams', 'available', 'free time',
            'discuss', 'catch up', 'sync', 'standup'
        ]
        
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in meeting_keywords)
    
    def extract_dates_and_times(self, text: str) -> List[str]:
        """Extract potential dates and times from text"""
        if not text:
            return []
        
        # Simple regex patterns for common date/time formats
        patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # MM/DD/YYYY or MM-DD-YYYY
            r'\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\b',  # Time with AM/PM
            r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',  # Days of week
            r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b'  # Month Day
        ]
        
        found_dates = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            found_dates.extend(matches)
        
        return found_dates