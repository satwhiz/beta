# agents/email_classifier_agent.py
from typing import Dict, List
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from models.email_models import EmailMessage, EmailLabel
from models.response_models import ThreadClassificationResponse
from agents.thread_email_classifier import ThreadEmailClassifier
from utils.thread_organizer import ThreadOrganizer
from loguru import logger

class EmailClassifierAgent(Agent):
    """Agent responsible for AI-powered email classification"""
    
    def __init__(self):
        super().__init__(
            name="Email Classifier Agent",
            role="Classify emails using AI into appropriate labels",
            model=OpenAIChat(id="gpt-4o"),
            instructions=[
                "You are an expert email classifier using thread-based analysis",
                "Classify emails into: to do, awaiting reply, fyi, done, spam",
                "Use thread context to understand conversation flow",
                "Provide high confidence classifications with clear reasoning",
                "Focus on actionability and user intent"
            ]
        )
        
        # Initialize the thread classifier
        self.thread_classifier = ThreadEmailClassifier()
        self.thread_organizer = ThreadOrganizer()
    
    def classify_emails(self, emails: List[EmailMessage]) -> Dict:
        """
        Classify a list of emails using thread-based analysis
        
        Args:
            emails: List of EmailMessage objects to classify
            
        Returns:
            Dict with classification results
        """
        try:
            logger.info(f"Classifying {len(emails)} emails using thread-based analysis")
            
            if not emails:
                return {
                    'total_emails': 0,
                    'classifications': [],
                    'label_distribution': {},
                    'threads_processed': 0
                }
            
            # Organize emails by threads
            threads = self.thread_organizer.organize_emails_by_thread(emails)
            logger.info(f"Organized {len(emails)} emails into {len(threads)} threads")
            
            # Classify each thread
            classifications = []
            label_counts = {}
            
            for thread_id, thread_emails in threads.items():
                try:
                    # Classify the thread
                    thread_classification = self.thread_classifier.classify_thread(thread_emails)
                    
                    # Create classification result for each email in thread
                    for email in thread_emails:
                        classification_result = {
                            'email_id': email.id,
                            'thread_id': thread_id,
                            'subject': email.subject,
                            'from_email': email.from_email,
                            'label': thread_classification.label.value,
                            'confidence': thread_classification.confidence,
                            'reasoning': thread_classification.reasoning,
                            'thread_email_count': len(thread_emails)
                        }
                        
                        classifications.append(classification_result)
                        
                        # Count labels
                        label = thread_classification.label.value
                        label_counts[label] = label_counts.get(label, 0) + 1
                
                except Exception as e:
                    logger.error(f"Error classifying thread {thread_id}: {str(e)}")
                    
                    # Fallback classification for thread
                    for email in thread_emails:
                        classifications.append({
                            'email_id': email.id,
                            'thread_id': thread_id,
                            'subject': email.subject,
                            'from_email': email.from_email,
                            'label': 'fyi',  # Safe fallback
                            'confidence': 0.3,
                            'reasoning': f"Classification error, fallback to FYI: {str(e)}",
                            'thread_email_count': len(thread_emails)
                        })
                        
                        label_counts['fyi'] = label_counts.get('fyi', 0) + 1
            
            result = {
                'total_emails': len(emails),
                'threads_processed': len(threads),
                'classifications': classifications,
                'label_distribution': label_counts,
                'success': True
            }
            
            logger.info(f"Classification complete: {len(classifications)} emails classified")
            logger.info(f"Label distribution: {label_counts}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in email classification: {str(e)}")
            return {
                'total_emails': len(emails),
                'classifications': [],
                'label_distribution': {},
                'threads_processed': 0,
                'success': False,
                'error': str(e)
            }
    
    def classify_single_email(self, email: EmailMessage, 
                            thread_context: List[EmailMessage] = None) -> Dict:
        """
        Classify a single email with optional thread context
        
        Args:
            email: EmailMessage to classify
            thread_context: Optional list of related emails in thread
            
        Returns:
            Dict with classification result
        """
        try:
            logger.info(f"Classifying single email: {email.subject}")
            
            # If no thread context provided, treat as single-email thread
            thread_emails = thread_context if thread_context else [email]
            
            # Classify the thread
            thread_classification = self.thread_classifier.classify_thread(thread_emails)
            
            result = {
                'email_id': email.id,
                'thread_id': email.thread_id,
                'subject': email.subject,
                'from_email': email.from_email,
                'label': thread_classification.label.value,
                'confidence': thread_classification.confidence,
                'reasoning': thread_classification.reasoning,
                'thread_email_count': len(thread_emails),
                'success': True
            }
            
            logger.info(f"Single email classified as: {thread_classification.label.value}")
            return result
            
        except Exception as e:
            logger.error(f"Error classifying single email: {str(e)}")
            return {
                'email_id': email.id,
                'thread_id': email.thread_id,
                'subject': email.subject,
                'from_email': email.from_email,
                'label': 'fyi',  # Safe fallback
                'confidence': 0.3,
                'reasoning': f"Classification error: {str(e)}",
                'thread_email_count': 1,
                'success': False,
                'error': str(e)
            }
    
    def get_classification_stats(self, classifications: List[Dict]) -> Dict:
        """
        Get statistics about classifications
        
        Args:
            classifications: List of classification results
            
        Returns:
            Dict with statistics
        """
        try:
            if not classifications:
                return {
                    'total_classifications': 0,
                    'average_confidence': 0,
                    'label_distribution': {},
                    'confidence_distribution': {}
                }
            
            # Calculate statistics
            total = len(classifications)
            confidences = [c['confidence'] for c in classifications if 'confidence' in c]
            average_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Label distribution
            label_counts = {}
            for classification in classifications:
                label = classification.get('label', 'unknown')
                label_counts[label] = label_counts.get(label, 0) + 1
            
            # Confidence distribution
            confidence_ranges = {
                'high (0.8-1.0)': 0,
                'medium (0.5-0.8)': 0,
                'low (0.0-0.5)': 0
            }
            
            for conf in confidences:
                if conf >= 0.8:
                    confidence_ranges['high (0.8-1.0)'] += 1
                elif conf >= 0.5:
                    confidence_ranges['medium (0.5-0.8)'] += 1
                else:
                    confidence_ranges['low (0.0-0.5)'] += 1
            
            return {
                'total_classifications': total,
                'average_confidence': round(average_confidence, 3),
                'label_distribution': label_counts,
                'confidence_distribution': confidence_ranges
            }
            
        except Exception as e:
            logger.error(f"Error calculating classification stats: {str(e)}")
            return {'error': str(e)}
    
    def filter_by_label(self, classifications: List[Dict], label: str) -> List[Dict]:
        """
        Filter classifications by specific label
        
        Args:
            classifications: List of classification results
            label: Label to filter by
            
        Returns:
            List of classifications with specified label
        """
        try:
            filtered = [c for c in classifications if c.get('label') == label]
            logger.info(f"Filtered {len(filtered)} classifications with label '{label}'")
            return filtered
            
        except Exception as e:
            logger.error(f"Error filtering by label: {str(e)}")
            return []
    
    def get_actionable_emails(self, classifications: List[Dict]) -> List[Dict]:
        """
        Get emails that require action (to do and awaiting reply)
        
        Args:
            classifications: List of classification results
            
        Returns:
            List of actionable email classifications
        """
        try:
            actionable_labels = ['to do', 'awaiting reply']
            actionable = [
                c for c in classifications 
                if c.get('label') in actionable_labels
            ]
            
            logger.info(f"Found {len(actionable)} actionable emails")
            return actionable
            
        except Exception as e:
            logger.error(f"Error getting actionable emails: {str(e)}")
            return []
    
    def get_inbox_emails(self, classifications: List[Dict]) -> List[Dict]:
        """
        Get emails that should remain in inbox (only 'to do')
        
        Args:
            classifications: List of classification results
            
        Returns:
            List of classifications that should stay in inbox
        """
        try:
            inbox_emails = [
                c for c in classifications 
                if c.get('label') == 'to do'
            ]
            
            logger.info(f"Found {len(inbox_emails)} emails that should stay in inbox")
            return inbox_emails
            
        except Exception as e:
            logger.error(f"Error getting inbox emails: {str(e)}")
            return []