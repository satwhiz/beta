from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

class EmailLabel(str, Enum):
    TODO = "to do"
    AWAITING_REPLY = "awaiting reply"
    FYI = "fyi"
    DONE = "done"
    SPAM = "spam"
    HISTORY = "history"

class EmailMessage(BaseModel):
    id: str
    thread_id: str
    from_email: str
    to_emails: List[str]
    cc_emails: Optional[List[str]] = []
    bcc_emails: Optional[List[str]] = []
    subject: str
    content: str
    date: datetime
    labels: List[str] = []
    is_thread_latest: bool = False

class EmailThread(BaseModel):
    thread_id: str
    messages: List[EmailMessage]
    latest_message: EmailMessage
    subject: str
    participants: List[str]
    created_date: datetime
    last_activity: datetime

class ClassifiedEmail(BaseModel):
    email: EmailMessage
    assigned_label: EmailLabel
    confidence: float
    reasoning: str

class EmailDraft(BaseModel):
    thread_id: str
    to_emails: List[str]
    cc_emails: Optional[List[str]] = []
    bcc_emails: Optional[List[str]] = []
    subject: str
    content: str
    context_used: List[str]
    calendar_context: Optional[Dict] = None