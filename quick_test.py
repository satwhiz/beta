# quick_test.py - Quick test of the agentic system
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

def test_system():
    """Quick test of the agentic email system"""
    print("🧪 Quick Test of Agentic Email System")
    print("=" * 40)
    
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found!")
        return False
    
    if not os.path.exists('credentials.json'):
        print("❌ credentials.json not found!")
        return False
    
    print("✅ Prerequisites check passed")
    
    try:
        # Test imports
        print("\n🔧 Testing imports...")
        from main import AgenticEmailSystem
        print("✅ Main system import successful")
        
        # Initialize system
        print("\n🤖 Initializing system...")
        system = AgenticEmailSystem()
        print("✅ System initialized successfully")
        
        # Test user stats (should work even without registration)
        print("\n📊 Testing user stats...")
        test_email = "gaurav@whizmail.ai"
        stats_result = system.get_user_stats(test_email)
        
        if stats_result['success']:
            print("✅ User found in database")
            user_info = stats_result['user_info']
            print(f"   Email: {user_info['email']}")
            print(f"   Processed emails: {user_info['total_emails_processed']}")
            print(f"   Labels applied: {user_info['labels_applied']}")
        else:
            print(f"ℹ️  User not found (expected for new users): {stats_result.get('error', 'Unknown')}")
        
        print("\n✅ Quick test completed successfully!")
        print("🚀 System is ready for use")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_system()