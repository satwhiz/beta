# models/response_models.py - Updated with thread-based responses
from pydantic import BaseModel
from typing import List, Optional, Dict
from models.email_models import EmailLabel, EmailMessage

# Keep existing models and add new thread-based ones

class EmailClassificationResponse(BaseModel):
    email_id: str
    label: EmailLabel
    confidence: float
    reasoning: str

class EmailFetchResponse(BaseModel):
    emails: List[EmailMessage]
    total_count: int
    success: bool
    error_message: Optional[str] = None

class DraftGenerationResponse(BaseModel):
    draft: Optional[object] = None  # EmailDraft
    success: bool
    error_message: Optional[str] = None

class ContextRetrievalResponse(BaseModel):
    relevant_emails: List[EmailMessage]
    context_summary: str
    similarity_scores: List[float]

class CalendarContextResponse(BaseModel):
    free_slots: List[Dict]
    upcoming_meetings: List[Dict]
    availability_summary: str

class InboxPrioritizationResponse(BaseModel):
    emails_for_inbox: List[str]
    reasoning: List[str]

# New thread-based models
class ThreadClassificationResponse(BaseModel):
    thread_id: str
    label: EmailLabel
    confidence: float
    reasoning: str
    email_count: int

class ThreadInfo(BaseModel):
    thread_id: str
    emails: List[EmailMessage]
    participants: List[str]
    subject: str
    start_date: str
    last_activity: str
    email_count: int

class ThreadProcessingResponse(BaseModel):
    threads_processed: int
    classifications: List[ThreadClassificationResponse]
    thread_info: List[ThreadInfo]
    success: bool
    error_message: Optional[str] = None