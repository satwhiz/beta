import os
from pydantic import BaseModel
from typing import List, Optional

class Settings(BaseModel):
    # Gmail API
    GMAIL_SCOPES: List[str] = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.compose'
    ]
    
    # Google Calendar API
    CALENDAR_SCOPES: List[str] = [
        'https://www.googleapis.com/auth/calendar.readonly'
    ]
    
    # Pinecone
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT", "us-west1-gcp")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "email-context")
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Email processing settings
    EMAIL_FETCH_LIMIT: int = int(os.getenv("EMAIL_FETCH_LIMIT", "100"))
    HISTORY_DAYS_THRESHOLD: int = int(os.getenv("HISTORY_DAYS_THRESHOLD", "5"))
    
    # File paths
    CREDENTIALS_FILE: str = os.getenv("CREDENTIALS_FILE", "credentials.json")
    TOKEN_FILE: str = os.getenv("TOKEN_FILE", "token.json")

settings = Settings()
