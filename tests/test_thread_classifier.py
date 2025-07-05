# tests/test_thread_classifier.py - Test thread classification independently
import os
import sys
from datetime import datetime, timedelta

# Fix Python path - get the parent directory (project root)
current_dir = os.path.dirname(os.path.abspath(__file__))  # tests directory
project_root = os.path.dirname(current_dir)  # parent directory (project root)
sys.path.insert(0, project_root)

print(f"Current dir: {current_dir}")
print(f"Project root: {project_root}")

from dotenv import load_dotenv
from models.email_models import EmailMessage
from agents.thread_email_classifier import ThreadEmailClassifier

def test_thread_classification():
    """Test thread classification with sample data"""
    print("🧵 Testing Thread-Based Email Classification")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("Please add OPENAI_API_KEY=your_key to your .env file")
        return
    
    print("✅ OpenAI API key found")
    
    # Initialize classifier
    classifier = ThreadEmailClassifier()
    
    # Use recent dates to avoid 5-day rule
    base_date = datetime.now() - timedelta(hours=2)  # 2 hours ago
    
    # Test Case 1: Simple To Do thread
    print("\n📧 Test Case 1: Simple Action Request Thread")
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
    
    # Test Case 2: Multi-email conversation thread (DONE)
    print("\n📧 Test Case 2: Multi-Email Conversation Thread (DONE)")
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
    
    # Test Case 3: Awaiting Reply thread
    print("\n📧 Test Case 3: Awaiting Reply Thread")
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
    
    # Test Case 4: FYI thread
    print("\n📧 Test Case 4: FYI Thread")
    thread4_emails = [
        EmailMessage(
            id="email_4_1",
            thread_id="thread_4",
            from_email="hr@company.com",
            to_emails=["gaurav@whizmail.ai", "team@company.com"],
            subject="New Company Policy Update",
            content="Please find attached the updated remote work policy that goes into effect next month. No action required, just for your information.",
            date=base_date
        )
    ]
    
    result4 = classifier.classify_thread(thread4_emails)
    print(f"🏷️  Classification: {result4.label.value}")
    print(f"🎯 Confidence: {result4.confidence:.2f}")
    print(f"💭 Reasoning: {result4.reasoning}")
    
    # Test Case 5: Spam thread
    print("\n📧 Test Case 5: Spam Thread")
    thread5_emails = [
        EmailMessage(
            id="email_5_1",
            thread_id="thread_5",
            from_email="noreply@marketing.com",
            to_emails=["gaurav@whizmail.ai"],
            subject="Flash Sale: 50% Off Everything!",
            content="Don't miss our biggest sale of the year! 50% off all items this weekend only. Use code SAVE50 at checkout. Limited time offer!",
            date=base_date
        )
    ]
    
    result5 = classifier.classify_thread(thread5_emails)
    print(f"🏷️  Classification: {result5.label.value}")
    print(f"🎯 Confidence: {result5.confidence:.2f}")
    print(f"💭 Reasoning: {result5.reasoning}")
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 THREAD CLASSIFICATION SUMMARY")
    print(f"{'='*50}")
    
    results = [result1, result2, result3, result4, result5]
    test_names = ["Action Request", "Meeting Coordination", "Awaiting Reply", "FYI Update", "Marketing Email"]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        print(f"{i+1}. {name:20}: {result.label.value.upper():15} (confidence: {result.confidence:.2f})")
    
    # Calculate average confidence
    avg_confidence = sum(r.confidence for r in results) / len(results)
    print(f"\nAverage Confidence: {avg_confidence:.2f}")
    
    print(f"\n✅ Thread classification test completed!")
    print("🧵 All threads classified based on conversation flow and context")

if __name__ == "__main__":
    test_thread_classification()