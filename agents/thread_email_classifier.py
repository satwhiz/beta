# agents/thread_email_classifier.py - Thread-based email classification
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from typing import List, Dict, Optional
from models.email_models import EmailMessage, EmailLabel
from models.response_models import ThreadClassificationResponse
from tools.text_processing import TextProcessing
from utils.date_utils import DateUtils
from config.settings import settings
from config.classification_prompts import THREAD_CLASSIFIER_SYSTEM_PROMPT, THREAD_CLASSIFICATION_PROMPT_TEMPLATE
from loguru import logger
import re

class ThreadEmailClassifier(Agent):
    def __init__(self):
        super().__init__(
            name="Thread Email Classifier Agent",
            role="Classify entire email threads with contextual understanding",
            model=OpenAIChat(id="gpt-4o"),
            instructions=[
                "You are an expert thread-based email classifier",
                "Analyze entire email threads to understand conversation flow",
                "Consider the progression: first email → response → counter-response",
                "Apply the 5-day rule for History classification automatically",
                "Provide reasoning based on thread evolution"
            ]
        )
        self.text_processor = TextProcessing()
        self.date_utils = DateUtils()
        self.system_prompt = THREAD_CLASSIFIER_SYSTEM_PROMPT
    
    def classify_thread(self, thread_emails: List[EmailMessage]) -> ThreadClassificationResponse:
        """
        Classify an entire email thread based on conversation flow
        
        Args:
            thread_emails: List of EmailMessage objects in chronological order
            
        Returns:
            ThreadClassificationResponse with single label for entire thread
        """
        try:
            if not thread_emails:
                return ThreadClassificationResponse(
                    thread_id="unknown",
                    label=EmailLabel.FYI,
                    confidence=0.0,
                    reasoning="No emails in thread",
                    email_count=0
                )
            
            # Sort emails by date to ensure chronological order
            sorted_emails = sorted(thread_emails, key=lambda x: x.date)
            
            # Check if entire thread is older than threshold
            latest_email = sorted_emails[-1]
            if self.date_utils.is_older_than_days(latest_email.date, settings.HISTORY_DAYS_THRESHOLD):
                return ThreadClassificationResponse(
                    thread_id=sorted_emails[0].thread_id,
                    label=EmailLabel.HISTORY,
                    confidence=1.0,
                    reasoning="Entire thread is older than 5 days - automatically classified as History",
                    email_count=len(sorted_emails)
                )
            
            # Build progressive context for classification
            thread_context = self._build_thread_context(sorted_emails)
            
            # Format the classification prompt
            classification_prompt = THREAD_CLASSIFICATION_PROMPT_TEMPLATE.format(
                system_prompt=self.system_prompt,
                thread_context=thread_context,
                email_count=len(sorted_emails),
                thread_id=sorted_emails[0].thread_id
            )
            
            # Get AI classification
            response = self.run(classification_prompt)
            
            # Parse the structured response
            label, confidence, reasoning = self._parse_classification_response(response.content)
            
            return ThreadClassificationResponse(
                thread_id=sorted_emails[0].thread_id,
                label=label,
                confidence=confidence,
                reasoning=reasoning,
                email_count=len(sorted_emails)
            )
            
        except Exception as e:
            logger.error(f"Error classifying thread: {str(e)}")
            return ThreadClassificationResponse(
                thread_id=thread_emails[0].thread_id if thread_emails else "unknown",
                label=EmailLabel.FYI,
                confidence=0.3,
                reasoning=f"Classification error: {str(e)}",
                email_count=len(thread_emails)
            )
    
    def _build_thread_context(self, sorted_emails: List[EmailMessage]) -> str:
        """Build progressive thread context showing email-by-email evolution"""
        context_parts = []
        
        for i, email in enumerate(sorted_emails):
            email_num = i + 1
            
            # Clean content
            cleaned_content = self.text_processor.clean_email_content(email.content)
            
            # Summarize if too long
            if len(cleaned_content) > 300:
                cleaned_content = self.text_processor.summarize_text(cleaned_content, 2)
            
            # Determine sender type (simplified)
            if i == 0:
                sender_context = "INITIATOR"
            else:
                # Check if same sender as previous
                prev_sender = sorted_emails[i-1].from_email
                if email.from_email == prev_sender:
                    sender_context = "SAME_SENDER"
                else:
                    sender_context = "RESPONDER"
            
            # Format email in context
            email_context = f"""
EMAIL {email_num} ({sender_context}):
From: {email.from_email}
To: {', '.join(email.to_emails)}
Subject: {email.subject}
Date: {email.date.strftime('%Y-%m-%d %H:%M')}
Content: {cleaned_content}
"""
            
            context_parts.append(email_context)
            
            # Add relationship to previous emails
            if i > 0:
                context_parts.append(f"\n--- EMAIL {email_num} builds upon EMAIL(S) 1-{i} ---\n")
        
        return "\n".join(context_parts)
    
    def classify_multiple_threads(self, threads: Dict[str, List[EmailMessage]]) -> List[ThreadClassificationResponse]:
        """Classify multiple email threads"""
        classifications = []
        
        for thread_id, thread_emails in threads.items():
            logger.info(f"Classifying thread {thread_id} with {len(thread_emails)} emails")
            classification = self.classify_thread(thread_emails)
            classifications.append(classification)
        
        return classifications
    
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
            reasoning_match = re.search(r'Reasoning:\s*(.+)', response, re.IGNORECASE | re.DOTALL)
            
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
                confidence = max(0.0, min(1.0, confidence_value))
            
            # Parse reasoning
            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()
                # Clean up reasoning (remove extra whitespace, limit length)
                reasoning = re.sub(r'\s+', ' ', reasoning)
                reasoning = reasoning[:400] + "..." if len(reasoning) > 400 else reasoning
            
            return label, confidence, reasoning
            
        except Exception as e:
            logger.error(f"Error parsing classification response: {str(e)}")
            logger.debug(f"Response content: {response}")
            
            # Fallback parsing
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
            
            return label, 0.5, f"Fallback parsing: {str(e)}"