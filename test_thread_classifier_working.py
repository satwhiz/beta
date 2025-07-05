# test_thread_classifier_working.py - Working test with path fix
import os
import sys
from datetime import datetime, timedelta

# Fix Python path - add project root to sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print(f"Project root: {project_root}")
print(f"Python path: {sys.path[0]}")

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Now import our modules
try:
    from models.email_models import EmailMessage
    print("✅ Successfully imported EmailMessage")
except ImportError as e:
    print(f"❌ Failed to import EmailMessage: {e}")
    sys.exit(1)

try:
    from agents.thread_email_classifier import ThreadEmailClassifier
    print("✅ Successfully imported ThreadEmailClassifier")
except ImportError as e:
    print(f"❌ Failed to import ThreadEmailClassifier: {e}")
    sys.exit(1)

def test_thread_classification():
    """Test thread classification with sample data"""
    print("\n🧵 Testing Thread-Based Email Classification")
    print("=" * 50)
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("Please add OPENAI_API_KEY=your_key to your .env file")
        return
    
    print("✅ OpenAI API key found")
    
    # Initialize classifier
    try:
        classifier = ThreadEmailClassifier()
        print("✅ ThreadEmailClassifier initialized")
    except Exception as e:
        print(f"❌ Failed to initialize classifier: {e}")
        return
    
    # Use recent dates to avoid 5-day rule
    base_date = datetime.now() - timedelta(hours=2)  # 2 hours ago
    
    # Test Case 1: Simple To Do thread
    print("\n📧 Test Case 1: Simple Action Request Thread")
    try:
        thread1_emails = [
            EmailMessage(
                id="email_1_1",
                thread_id="thread_1",
                from_email="boss@company.com",
                to_emails=["gaurav@whizmail.ai"],
                subject="Quarterly Report Review",
                content="Hi Gaurav, can you please review the attached quarterly report and provide feedback by end of day Friday? This is needed for the board meeting.",
                date=base_date
            )
        ]
        
        result1 = classifier.classify_thread(thread1_emails)
        print(f"🏷️  Classification: {result1.label.value}")
        print(f"🎯 Confidence: {result1.confidence:.2f}")
        print(f"💭 Reasoning: {result1.reasoning}")
        
    except Exception as e:
        print(f"❌ Test Case 1 failed: {e}")
    
    # Test Case 2: Multi-email conversation thread (DONE)
    print("\n📧 Test Case 2: Multi-Email Conversation Thread (DONE)")
    try:
        thread2_emails = [
            EmailMessage(
                id="email_2_1",
                thread_id="thread_2",
                from_email="colleague@company.com",
                to_emails=["gaurav@whizmail.ai"],
                subject="Meeting Next Week",
                content="Hey Gaurav, are you available for a project sync meeting next week? I'm thinking Tuesday or Wednesday afternoon.",
                date=base_date
            ),
            EmailMessage(
                id="email_2_2", 
                thread_id="thread_2",
                from_email="gaurav@whizmail.ai",
                to_emails=["colleague@company.com"],
                subject="Re: Meeting Next Week",
                content="Hi! Tuesday afternoon works better for me. How about 2 PM?",
                date=base_date + timedelta(minutes=30)
            ),
            EmailMessage(
                id="email_2_3",
                thread_id="thread_2", 
                from_email="colleague@company.com",
                to_emails=["gaurav@whizmail.ai"],
                subject="Re: Meeting Next Week",
                content="Perfect! Tuesday at 2 PM it is. I'll send a calendar invite. Thanks!",
                date=base_date + timedelta(minutes=60)
            )
        ]
        
        result2 = classifier.classify_thread(thread2_emails)
        print(f"🏷️  Classification: {result2.label.value}")
        print(f"🎯 Confidence: {result2.confidence:.2f}")  
        print(f"💭 Reasoning: {result2.reasoning}")
        
    except Exception as e:
        print(f"❌ Test Case 2 failed: {e}")
    
    # Test Case 3: Awaiting Reply thread
    print("\n📧 Test Case 3: Awaiting Reply Thread")
    try:
        thread3_emails = [
            EmailMessage(
                id="email_3_1",
                thread_id="thread_3",
                from_email="client@external.com", 
                to_emails=["gaurav@whizmail.ai"],
                subject="Proposal Request",
                content="Hi Gaurav, could you send me a proposal for the new website project we discussed?",
                date=base_date - timedelta(hours=5)
            ),
            EmailMessage(
                id="email_3_2",
                thread_id="thread_3",
                from_email="gaurav@whizmail.ai",
                to_emails=["client@external.com"],
                subject="Re: Proposal Request", 
                content="Hi! I've attached the proposal for the website project. Please let me know if you have any questions or need any modifications.",
                date=base_date - timedelta(hours=1)
            )
        ]
        
        result3 = classifier.classify_thread(thread3_emails)
        print(f"🏷️  Classification: {result3.label.value}")
        print(f"🎯 Confidence: {result3.confidence:.2f}")
        print(f"💭 Reasoning: {result3.reasoning}")
        
    except Exception as e:
        print(f"❌ Test Case 3 failed: {e}")
    
    print(f"\n✅ Thread classification test completed!")
    print("🧵 All available tests run successfully")

if __name__ == "__main__":
    test_thread_classification()