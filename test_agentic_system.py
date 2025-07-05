# test_agentic_system.py - Test script for the agentic email system
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from main import AgenticEmailSystem
import time

def test_user_registration():
    """Test user registration process"""
    print("🧪 Testing User Registration")
    print("=" * 40)
    
    system = AgenticEmailSystem()
    test_email = "test@example.com"  # Replace with your test email
    
    print(f"Registering user: {test_email}")
    result = system.register_new_user(test_email)
    
    if result['success']:
        print("✅ User registration successful!")
        print(f"   User: {result['user_email']}")
        print(f"   Created: {result.get('created_at', 'Unknown')}")
        
        if 'initial_processing' in result:
            proc = result['initial_processing']
            print(f"   Initial emails processed: {proc.get('emails_processed', 0)}")
            print(f"   Labels applied: {proc.get('labels_applied', 0)}")
        
        return True
    else:
        print(f"❌ Registration failed: {result.get('error', 'Unknown error')}")
        return False

def test_email_processing():
    """Test email processing for existing emails"""
    print("\n🧪 Testing Email Processing")
    print("=" * 40)
    
    system = AgenticEmailSystem()
    test_email = "test@example.com"  # Replace with your test email
    
    print(f"Processing existing emails for: {test_email}")
    result = system.process_existing_emails(test_email, limit=20)
    
    if result['success']:
        print("✅ Email processing successful!")
        print(f"   Emails processed: {result.get('emails_processed', 0)}")
        print(f"   History emails: {result.get('history_count', 0)}")
        print(f"   Classified emails: {result.get('classified_count', 0)}")
        print(f"   Inbox 'to do' emails: {result.get('inbox_todo_count', 0)}")
        
        if 'label_distribution' in result:
            print("   Label Distribution:")
            for label, count in result['label_distribution'].items():
                print(f"     {label}: {count}")
        
        return True
    else:
        print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
        return False

def test_user_stats():
    """Test getting user statistics"""
    print("\n🧪 Testing User Statistics")
    print("=" * 40)
    
    system = AgenticEmailSystem()
    test_email = "test@example.com"  # Replace with your test email
    
    result = system.get_user_stats(test_email)
    
    if result['success']:
        print("✅ User stats retrieved!")
        user_info = result['user_info']
        stats = result['processing_stats']
        
        print(f"   Email: {user_info['email']}")
        print(f"   Registered: {user_info.get('created_at', 'Unknown')}")
        print(f"   Last processed: {user_info.get('last_processed_at', 'Never')}")
        print(f"   Total processed: {stats.get('total_processed', 0)}")
        print(f"   Labels applied: {stats.get('labels_applied', 0)}")
        print(f"   Current inbox: {stats.get('inbox_count', 0)}")
        
        return True
    else:
        print(f"❌ Stats retrieval failed: {result.get('error', 'Unknown error')}")
        return False

def test_monitoring_setup():
    """Test email monitoring setup"""
    print("\n🧪 Testing Email Monitoring Setup")
    print("=" * 40)
    
    system = AgenticEmailSystem()
    test_email = "test@example.com"  # Replace with your test email
    
    result = system.start_email_monitoring(test_email)
    
    if result['success']:
        print("✅ Email monitoring setup successful!")
        print(f"   User: {result['user_email']}")
        print(f"   Monitoring active: {result['monitoring_active']}")
        return True
    else:
        print(f"❌ Monitoring setup failed: {result.get('error', 'Unknown error')}")
        return False

def test_label_revert():
    """Test label reversal for testing"""
    print("\n🧪 Testing Label Reversal")
    print("=" * 40)
    
    system = AgenticEmailSystem()
    test_email = "gaurav@whizmail.ai"  # Replace with your test email
    
    confirm = input("⚠️  This will revert all applied labels. Continue? (y/N): ")
    if confirm.lower() != 'y':
        print("❌ Revert cancelled")
        return False
    
    result = system.revert_user_labels(test_email)
    
    if result['success']:
        print("✅ Label reversal successful!")
        print(f"   Labels reverted: {result.get('reverted_count', 0)}")
        return True
    else:
        print(f"❌ Revert failed: {result.get('error', 'Unknown error')}")
        return False

def run_comprehensive_test():
    """Run a comprehensive test of the agentic system"""
    print("🤖 Comprehensive Agentic Email System Test")
    print("=" * 50)
    
    # Check prerequisites
    print("Checking prerequisites...")
    
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("Please create .env with OPENAI_API_KEY")
        return
    
    if not os.path.exists('credentials.json'):
        print("❌ credentials.json not found!")
        print("Please download from Google Cloud Console")
        return
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in environment!")
        return
    
    print("✅ Prerequisites check passed")
    
    # Get test email
    test_email = input("\nEnter test email address: ").strip()
    if not test_email or '@' not in test_email:
        print("❌ Invalid email address")
        return
    
    print(f"\n🎯 Testing with email: {test_email}")
    print("This will:")
    print("1. Register the user (OAuth required)")
    print("2. Process existing emails") 
    print("3. Apply AI-based labels")
    print("4. Manage inbox (only 'to do' emails remain)")
    print("5. Setup monitoring")
    
    proceed = input("\nProceed with comprehensive test? (y/N): ")
    if proceed.lower() != 'y':
        print("Test cancelled")
        return
    
    # Run tests in sequence
    tests = [
        ("User Registration", lambda: test_user_registration_with_email(test_email)),
        ("Email Processing", lambda: test_email_processing_with_email(test_email)),
        ("User Statistics", lambda: test_user_stats_with_email(test_email)),
        ("Monitoring Setup", lambda: test_monitoring_setup_with_email(test_email))
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Running: {test_name}")
        print(f"{'='*60}")
        
        try:
            results[test_name] = test_func()
            if results[test_name]:
                print(f"✅ {test_name} - PASSED")
            else:
                print(f"❌ {test_name} - FAILED")
        except Exception as e:
            print(f"❌ {test_name} - ERROR: {str(e)}")
            results[test_name] = False
        
        # Small delay between tests
        time.sleep(2)
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:20}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Agentic email system is working correctly.")
        
        # Offer to revert for testing
        revert = input("\nRevert applied labels for clean testing? (y/N): ")
        if revert.lower() == 'y':
            test_label_revert_with_email(test_email)
    else:
        print("⚠️  Some tests failed. Check logs for details.")

def test_user_registration_with_email(email):
    """Helper function for comprehensive test"""
    system = AgenticEmailSystem()
    result = system.register_new_user(email)
    return result['success']

def test_email_processing_with_email(email):
    """Helper function for comprehensive test"""
    system = AgenticEmailSystem()
    result = system.process_existing_emails(email, limit=20)
    return result['success']

def test_user_stats_with_email(email):
    """Helper function for comprehensive test"""
    system = AgenticEmailSystem()
    result = system.get_user_stats(email)
    return result['success']

def test_monitoring_setup_with_email(email):
    """Helper function for comprehensive test"""
    system = AgenticEmailSystem()
    result = system.start_email_monitoring(email)
    return result['success']

def test_label_revert_with_email(email):
    """Helper function for comprehensive test"""
    system = AgenticEmailSystem()
    result = system.revert_user_labels(email)
    return result['success']

def show_menu():
    """Show interactive test menu"""
    print("\n🤖 Agentic Email System - Test Menu")
    print("=" * 40)
    print("1. 🧪 Run comprehensive test")
    print("2. 👤 Test user registration only")
    print("3. 📧 Test email processing only")
    print("4. 📊 Test user statistics only")
    print("5. 🔔 Test monitoring setup only")
    print("6. 🔄 Test label reversal only")
    print("7. 🚪 Exit")
    print()

def main():
    """Main test function"""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--comprehensive':
            run_comprehensive_test()
            return
        elif sys.argv[1] == '--help':
            print("Usage:")
            print("  python test_agentic_system.py --comprehensive  # Run full test")
            print("  python test_agentic_system.py                  # Interactive menu")
            return
    
    # Interactive menu
    while True:
        show_menu()
        choice = input("Enter choice (1-7): ").strip()
        
        try:
            if choice == '1':
                run_comprehensive_test()
            elif choice == '2':
                test_user_registration()
            elif choice == '3':
                test_email_processing()
            elif choice == '4':
                test_user_stats()
            elif choice == '5':
                test_monitoring_setup()
            elif choice == '6':
                test_label_revert()
            elif choice == '7':
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please try again.")
        
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()