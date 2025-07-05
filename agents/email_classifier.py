from agno.agent import Agent
from agno.models.openai import OpenAIChat
from typing import List, Dict
from models.email_models import EmailMessage, EmailLabel, ClassifiedEmail
from models.response_models import EmailClassificationResponse
from tools.text_processing import TextProcessing
from utils.date_utils import DateUtils
from config.settings import settings
from config.classification_prompts import GMAIL_CLASSIFIER_SYSTEM_PROMPT, CLASSIFICATION_PROMPT_TEMPLATE
from loguru import logger
import re

class EmailClassifierAgent(Agent):
    def __init__(self):
        super().__init__(
            name="Email Classifier Agent",
            role="Classify emails into appropriate labels using detailed classification rules",
            model=OpenAIChat(id="gpt-4o"),
            instructions=[
                "You are an expert Gmail email classifier",
                "Follow the detailed classification system with strict rules and decision sequence",
                "Always provide classification, confidence score, and reasoning",
                "Consider thread context when available",
                "Apply the 5-day rule for History classification automatically"
            ]
        )
        self.text_processor = TextProcessing()
        self.date_utils = DateUtils()
        self.system_prompt = GMAIL_CLASSIFIER_SYSTEM_PROMPT
    
    def classify_email(self, email: EmailMessage, thread_context: List[EmailMessage] = None) -> EmailClassificationResponse:
        """Classify a single email using the detailed classification system"""
        try:
            # Check if email is older than threshold - automatic History classification
            if self.date_utils.is_older_than_days(email.date, settings.HISTORY_DAYS_THRESHOLD):
                return EmailClassificationResponse(
                    email_id=email.id,
                    label=EmailLabel.HISTORY,
                    confidence=1.0,
                    reasoning="Email is older than 5 days threshold - automatically classified as History"
                )
            
            # Prepare thread context for classification
            context_summary = self._prepare_thread_context(email, thread_context)
            
            # Format the classification prompt
            classification_prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(
                system_prompt=self.system_prompt,
                from_email=email.from_email,
                to_emails=", ".join(email.to_emails),
                subject=email.subject,
                date=email.date.strftime("%Y-%m-%d %H:%M:%S"),
                content=email.content[:1000] + "..." if len(email.content) > 1000 else email.content,
                thread_context=context_summary
            )
            
            # Get AI classification
            response = self.run(classification_prompt)
            
            # Parse the structured response
            label, confidence, reasoning = self._parse_classification_response(response.content)
            
            return EmailClassificationResponse(
                email_id=email.id,
                label=label,
                confidence=confidence,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Error classifying email {email.id}: {str(e)}")
            return EmailClassificationResponse(
                email_id=email.id,
                label=EmailLabel.FYI,  # Safe default
                confidence=0.3,
                reasoning=f"Classification error - defaulted to FYI: {str(e)}"
            )
    
    def classify_multiple_emails(self, emails: List[EmailMessage]) -> List[EmailClassificationResponse]:
        """Classify multiple emails efficiently"""
        classifications = []
        
        for email in emails:
            # Get thread context if available
            thread_context = None  # Could be enhanced to fetch actual thread context
            
            classification = self.classify_email(email, thread_context)
            classifications.append(classification)
            
            logger.info(f"Classified email {email.id} as {classification.label.value} (confidence: {classification.confidence})")
        
        return classifications
    
    def _prepare_thread_context(self, email: EmailMessage, thread_context: List[EmailMessage]) -> str:
        """Prepare thread context summary for classification"""
        if not thread_context:
            return "No thread context available"
        
        # Sort by date to get chronological order
        sorted_context = sorted(thread_context, key=lambda x: x.date)
        
        context_parts = []
        for i, msg in enumerate(sorted_context[-5:]):  # Last 5 messages for context
            # Identify if message is from user (simplified logic)
            is_from_user = msg.from_email == email.to_emails[0] if email.to_emails else False
            sender_type = "User" if is_from_user else "Other"
            
            summary = f"{sender_type}: {msg.subject[:50]}... - {self.text_processor.summarize_text(msg.content, 1)}"
            context_parts.append(summary)
        
        return " | ".join(context_parts)
    
    def _parse_classification_response(self, response: str) -> tuple:
        """Parse the structured AI response to extract classification details"""
        try:
            # Initialize defaults
            label = EmailLabel.FYI
            confidence = 0.5
            reasoning = "Unable to parse classification response"
            
            # Extract classification using regex patterns
            classification_match = re.search(r'Classification:\s*(.+)', response, re.IGNORECASE)
            confidence_match = re.search(r'Confidence:\s*([0-9.]+)', response, re.IGNORECASE)
            reasoning_match = re.search(r'Reasoning:\s*(.+)', response, re.IGNORECASE)
            
            # Parse classification label
            if classification_match:
                label_text = classification_match.group(1).strip().lower()
                
                # Map to EmailLabel enum
                if "to do" in label_text or "todo" in label_text:
                    label = EmailLabel.TODO
                elif "awaiting reply" in label_text or "awaiting" in label_text:
                    label = EmailLabel.AWAITING_REPLY
                elif "fyi" in label_text:
                    label = EmailLabel.FYI
                elif "done" in label_text:
                    label = EmailLabel.DONE
                elif "spam" in label_text:
                    label = EmailLabel.SPAM
                elif "history" in label_text:
                    label = EmailLabel.HISTORY
            
            # Parse confidence
            if confidence_match:
                confidence_value = float(confidence_match.group(1))
                # Ensure confidence is between 0 and 1
                confidence = max(0.0, min(1.0, confidence_value))
            
            # Parse reasoning
            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()
                # Limit reasoning length
                reasoning = reasoning[:200] + "..." if len(reasoning) > 200 else reasoning
            
            return label, confidence, reasoning
            
        except Exception as e:
            logger.error(f"Error parsing classification response: {str(e)}")
            logger.debug(f"Response content: {response}")
            
            # Fallback parsing - look for keywords in the response
            response_lower = response.lower()
            
            if "to do" in response_lower or "todo" in response_lower:
                label = EmailLabel.TODO
            elif "awaiting" in response_lower:
                label = EmailLabel.AWAITING_REPLY
            elif "spam" in response_lower:
                label = EmailLabel.SPAM
            elif "done" in response_lower:
                label = EmailLabel.DONE
            elif "history" in response_lower:
                label = EmailLabel.HISTORY
            else:
                label = EmailLabel.FYI
            
            return label, 0.5, f"Fallback parsing due to error: {str(e)}"