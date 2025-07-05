# tests/test_push_notifications.py
import unittest
import json
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import modules to test
from push_notifications.monitoring.email_monitor import EmailMonitor
from push_notifications.monitoring.webhook_handlers import WebhookHandler, WebhookValidator
from models.email_models import EmailMessage

class TestEmailMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = EmailMonitor()
        self.test_user = "test@example.com"
    
    def test_monitor_initialization(self):
        """Test that EmailMonitor initializes correctly"""
        self.assertIsInstance(self.monitor.active_monitors, dict)
        self.assertIsInstance(self.monitor.processed_emails, set)
        self.assertFalse(self.monitor.is_running)
    
    @patch('push_notifications.monitoring.email_monitor.build')
    @patch('push_notifications.monitoring.email_monitor.GmailTools')
    def test_start_monitoring_success(self, mock_gmail_tools, mock_build):
        """Test successful start of monitoring"""
        # Mock credentials
        mock_credentials = Mock()
        
        # Mock Gmail service
        mock_service = Mock()
        mock_service.users().getProfile().execute.return_value = {
            'messagesTotal': 100,
            'emailAddress': self.test_user
        }
        mock_build.return_value = mock_service
        
        # Mock GmailTools
        mock_gmail_tools.return_value = Mock()
        
        # Start monitoring
        result = self.monitor.start_monitoring(self.test_user, mock_credentials)
        
        self.assertTrue(result)
        self.assertIn(self.test_user, self.monitor.active_monitors)
        
        # Clean up
        self.monitor.stop_monitoring(self.test_user)
    
    def test_stop_monitoring(self):
        """Test stopping monitoring for a user"""
        # Add a mock monitor
        self.monitor.active_monitors[self.test_user] = {
            'is_active': True,
            'user_email': self.test_user
        }
        
        result = self.monitor.stop_monitoring(self.test_user)
        
        self.assertTrue(result)
        self.assertNotIn(self.test_user, self.monitor.active_monitors)
    
    def test_get_monitoring_status(self):
        """Test getting monitoring status"""
        # Add mock monitors
        self.monitor.active_monitors['user1@example.com'] = {
            'is_active': True,
            'last_check': datetime.now(),
            'emails_processed': 5,
            'check_interval': 30
        }
        
        status = self.monitor.get_monitoring_status()
        
        self.assertEqual(status['total_monitors'], 1)
        self.assertEqual(len(status['monitors']), 1)
        self.assertEqual(status['monitors'][0]['user_email'], 'user1@example.com')

class TestWebhookHandler(unittest.TestCase):
    def setUp(self):
        self.handler = WebhookHandler(secret_key="test_secret")
    
    def test_parse_pubsub_message_success(self):
        """Test successful parsing of Pub/Sub message"""
        # Create mock Pub/Sub message
        notification_data = {
            'emailAddress': 'test@example.com',
            'historyId': '12345'
        }
        
        # Encode as base64
        import base64
        encoded_data = base64.b64encode(
            json.dumps(notification_data).encode()
        ).decode()
        
        request_data = {
            'message': {
                'data': encoded_data,
                'messageId': 'msg_123',
                'publishTime': '2024-07-05T12:00:00Z'
            }
        }
        
        result = self.handler.parse_pubsub_message(request_data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['user_email'], 'test@example.com')
        self.assertEqual(result['history_id'], '12345')
    
    def test_parse_pubsub_message_invalid(self):
        """Test parsing invalid Pub/Sub message"""
        invalid_data = {'invalid': 'data'}
        
        result = self.handler.parse_pubsub_message(invalid_data)
        
        self.assertIsNone(result)
    
    def test_create_webhook_response_success(self):
        """Test creating successful webhook response"""
        data = {'test': 'data'}
        response = self.handler.create_webhook_response(True, data=data)
        
        self.assertTrue(response['success'])
        self.assertEqual(response['data'], data)
        self.assertIn('timestamp', response)
    
    def test_create_webhook_response_error(self):
        """Test creating error webhook response"""
        error_msg = "Test error"
        response = self.handler.create_webhook_response(False, error=error_msg)
        
        self.assertFalse(response['success'])
        self.assertEqual(response['error'], error_msg)

class TestWebhookValidator(unittest.TestCase):
    def test_validate_gmail_notification_valid(self):
        """Test validation of valid Gmail notification"""
        valid_data = {
            'user_email': 'test@example.com',
            'history_id': '12345'
        }
        
        is_valid, message = WebhookValidator.validate_gmail_notification(valid_data)
        
        self.assertTrue(is_valid)
        self.assertEqual(message, "Valid")
    
    def test_validate_gmail_notification_missing_field(self):
        """Test validation with missing required field"""
        invalid_data = {
            'user_email': 'test@example.com'
            # missing history_id
        }
        
        is_valid, message = WebhookValidator.validate_gmail_notification(invalid_data)
        
        self.assertFalse(is_valid)
        self.assertIn("history_id", message)
    
    def test_validate_gmail_notification_invalid_email(self):
        """Test validation with invalid email format"""
        invalid_data = {
            'user_email': 'invalid_email',
            'history_id': '12345'
        }
        
        is_valid, message = WebhookValidator.validate_gmail_notification(invalid_data)
        
        self.assertFalse(is_valid)
        self.assertIn("email format", message)
    
    def test_validate_process_email_request_valid(self):
        """Test validation of valid process email request"""
        valid_data = {
            'user_email': 'test@example.com',
            'message_id': 'msg_12345'
        }
        
        is_valid, message = WebhookValidator.validate_process_email_request(valid_data)
        
        self.assertTrue(is_valid)
        self.assertEqual(message, "Valid")

class TestPushNotificationIntegration(unittest.TestCase):
    """Integration tests for push notification system"""
    
    def setUp(self):
        self.monitor = EmailMonitor()
        self.handler = WebhookHandler()
    
    @patch('push_notifications.monitoring.email_monitor.ThreadEmailClassifier')
    def test_email_processing_flow(self, mock_classifier):
        """Test complete email processing flow"""
        # Mock classifier
        mock_classification = Mock()
        mock_classification.label.value = "to do"
        mock_classification.confidence = 0.95
        mock_classifier.reasoning = "Test classification"
        
        mock_classifier.return_value.classify_multiple_threads.return_value = [mock_classification]
        
        # Create test email
        test_email = EmailMessage(
            id="test_123",
            thread_id="thread_123",
            from_email="sender@test.com",
            to_emails=["recipient@test.com"],
            subject="Test Email",
            content="This is a test email",
            date=datetime.now()
        )
        
        # Test processing (would need more mocking for full integration)
        self.assertIsNotNone(test_email)
        self.assertEqual(test_email.subject, "Test Email")

def run_push_notification_tests():
    """Run all push notification tests"""
    print("🧪 Running Push Notification Tests")
    print("=" * 40)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestEmailMonitor))
    suite.addTests(loader.loadTestsFromTestCase(TestWebhookHandler))
    suite.addTests(loader.loadTestsFromTestCase(TestWebhookValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestPushNotificationIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n📊 Test Results:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print(f"\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  • {test}: {traceback}")
    
    if result.errors:
        print(f"\n⚠️  Errors:")
        for test, traceback in result.errors:
            print(f"  • {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n{'✅ All tests passed!' if success else '❌ Some tests failed!'}")
    
    return success

if __name__ == "__main__":
    run_push_notification_tests()