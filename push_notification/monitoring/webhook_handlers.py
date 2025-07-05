# push_notifications/monitoring/webhook_handlers.py
import json
import base64
import hmac
import hashlib
from typing import Dict, Optional
from flask import Request

class WebhookHandler:
    """Handle various types of webhook notifications"""
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key
    
    def verify_gmail_webhook(self, request: Request) -> bool:
        """Verify Gmail webhook signature"""
        try:
            if not self.secret_key:
                return True  # Skip verification if no secret set
            
            # Get signature from headers
            signature = request.headers.get('X-Goog-Signature')
            if not signature:
                return True  # Skip if no signature
            
            # Calculate expected signature
            expected_signature = hmac.new(
                self.secret_key.encode(),
                request.get_data(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            print(f"Error verifying webhook: {e}")
            return False
    
    def parse_pubsub_message(self, request_data: Dict) -> Optional[Dict]:
        """Parse Google Pub/Sub message from webhook"""
        try:
            # Extract message from Pub/Sub envelope
            envelope = request_data
            if not envelope:
                return None
            
            pubsub_message = envelope.get('message')
            if not pubsub_message:
                return None
            
            # Decode base64 data
            message_data = base64.b64decode(pubsub_message['data']).decode('utf-8')
            notification_data = json.loads(message_data)
            
            return {
                'user_email': notification_data.get('emailAddress'),
                'history_id': notification_data.get('historyId'),
                'message_id': pubsub_message.get('messageId'),
                'publish_time': pubsub_message.get('publishTime'),
                'attributes': pubsub_message.get('attributes', {})
            }
            
        except Exception as e:
            print(f"Error parsing Pub/Sub message: {e}")
            return None
    
    def create_webhook_response(self, success: bool, data: Dict = None, 
                              error: str = None) -> Dict:
        """Create standardized webhook response"""
        response = {
            'success': success,
            'timestamp': json.loads(json.dumps({}))  # Current timestamp
        }
        
        if success and data:
            response['data'] = data
        
        if not success and error:
            response['error'] = error
        
        return response
    
    def handle_gmail_notification(self, notification_data: Dict) -> Dict:
        """Handle Gmail push notification"""
        try:
            user_email = notification_data.get('user_email')
            history_id = notification_data.get('history_id')
            
            if not user_email or not history_id:
                return self.create_webhook_response(
                    False, 
                    error="Missing user_email or history_id"
                )
            
            # This would be processed by the email monitor
            result = {
                'notification_received': True,
                'user_email': user_email,
                'history_id': history_id,
                'processing_status': 'queued'
            }
            
            return self.create_webhook_response(True, result)
            
        except Exception as e:
            return self.create_webhook_response(False, error=str(e))

class WebhookValidator:
    """Validate webhook requests and data"""
    
    @staticmethod
    def validate_gmail_notification(data: Dict) -> tuple[bool, str]:
        """Validate Gmail notification data"""
        required_fields = ['user_email', 'history_id']
        
        for field in required_fields:
            if field not in data or not data[field]:
                return False, f"Missing required field: {field}"
        
        # Validate email format
        user_email = data['user_email']
        if '@' not in user_email or '.' not in user_email:
            return False, "Invalid email format"
        
        return True, "Valid"
    
    @staticmethod
    def validate_process_email_request(data: Dict) -> tuple[bool, str]:
        """Validate process email request"""
        required_fields = ['user_email', 'message_id']
        
        for field in required_fields:
            if field not in data or not data[field]:
                return False, f"Missing required field: {field}"
        
        return True, "Valid"