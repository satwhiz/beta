# setup_labels.py - FIXED: Complete Gmail label setup with proper SPAM handling
import os
import sys
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Load environment
load_dotenv()

class GmailLabelManager:
    """Enhanced Gmail label management with proper SPAM handling"""
    
    # Our complete required labels with Gmail-approved colors ONLY
    REQUIRED_LABELS = {
        'to do': {
            'name': '📋 To Do',
            'color': {'textColor': '#ffffff', 'backgroundColor': '#ff7537'},  # Gmail Orange
            'visibility': {'messageListVisibility': 'show', 'labelListVisibility': 'labelShow'}
        },
        'awaiting reply': {
            'name': '⏳ Awaiting Reply', 
            'color': {'textColor': '#ffffff', 'backgroundColor': '#ffad46'},  # Gmail Light Orange  
            'visibility': {'messageListVisibility': 'show', 'labelListVisibility': 'labelShow'}
        },
        'fyi': {
            'name': 'ℹ️ FYI',
            'color': {'textColor': '#ffffff', 'backgroundColor': '#16a766'},  # Gmail Green
            'visibility': {'messageListVisibility': 'show', 'labelListVisibility': 'labelShow'}
        },
        'done': {
            'name': '✅ Done',
            'color': {'textColor': '#ffffff', 'backgroundColor': '#0b804b'},  # Gmail Dark Green
            'visibility': {'messageListVisibility': 'show', 'labelListVisibility': 'labelShow'}
        },
        'spam': {
            'name': '🗑️ SPAM',
            'color': {'textColor': '#ffffff', 'backgroundColor': '#cc3a21'},  # Gmail Red
            'visibility': {'messageListVisibility': 'show', 'labelListVisibility': 'labelShow'}
        },
        'history': {
            'name': '📜 History',
            'color': {'textColor': '#ffffff', 'backgroundColor': '#8e63ce'},  # Gmail Purple
            'visibility': {'messageListVisibility': 'show', 'labelListVisibility': 'labelShow'}
        }
    }
    
    def __init__(self, credentials: Credentials):
        self.service = build('gmail', 'v1', credentials=credentials)
        self.existing_labels = {}
        self._load_existing_labels()
    
    def _load_existing_labels(self):
        """Load all existing labels from Gmail"""
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            # Create mapping of label names to label objects
            for label in labels:
                self.existing_labels[label['name'].lower()] = label
            
            print(f"📋 Found {len(labels)} existing labels in Gmail")
            
        except Exception as e:
            print(f"❌ Error loading existing labels: {e}")
    
    def check_our_labels_status(self) -> Dict:
        """Check status of our required labels only"""
        status = {
            'found': {},
            'missing': [],
            'total_required': len(self.REQUIRED_LABELS),
            'total_found': 0
        }
        
        for key, config in self.REQUIRED_LABELS.items():
            label_name = config['name']
            
            # Check if our label exists (exact match or similar)
            found_label = None
            
            # Check exact match first
            if label_name.lower() in self.existing_labels:
                found_label = self.existing_labels[label_name.lower()]
            else:
                # Check for similar names (for our labels)
                for existing_name, existing_label in self.existing_labels.items():
                    # Match our label patterns
                    if key == 'to do' and ('to do' in existing_name or 'todo' in existing_name):
                        found_label = existing_label
                        break
                    elif key == 'awaiting reply' and 'awaiting' in existing_name:
                        found_label = existing_label
                        break
                    elif key == 'fyi' and 'fyi' in existing_name:
                        found_label = existing_label
                        break
                    elif key == 'done' and 'done' in existing_name and 'undone' not in existing_name:
                        found_label = existing_label
                        break
                    elif key == 'spam' and ('spam' in existing_name or '🗑️' in existing_name) and existing_label.get('type') != 'system':
                        found_label = existing_label
                        break
                    elif key == 'history' and 'history' in existing_name:
                        found_label = existing_label
                        break
            
            if found_label:
                status['found'][key] = {
                    'id': found_label['id'],
                    'name': found_label['name'],
                    'type': found_label.get('type', 'user')
                }
                status['total_found'] += 1
            else:
                status['missing'].append(key)
        
        return status
    
    def create_or_update_label(self, key: str, config: Dict) -> Tuple[bool, str, str]:
        """
        Create or update a single label
        Returns: (success, action, message)
        """
        try:
            label_name = config['name']
            
            # Check if label exists
            existing_label = None
            
            # Look for existing label
            for existing_name, label_obj in self.existing_labels.items():
                if self._is_our_label(key, existing_name, label_obj):
                    existing_label = label_obj
                    break
            
            if existing_label:
                # Update existing label
                update_body = {
                    'name': label_name,
                    'color': config['color'],
                    'messageListVisibility': config['visibility']['messageListVisibility'],
                    'labelListVisibility': config['visibility']['labelListVisibility']
                }
                
                updated_label = self.service.users().labels().update(
                    userId='me',
                    id=existing_label['id'],
                    body=update_body
                ).execute()
                
                return True, 'updated', f"Updated: {label_name}"
            
            else:
                # Create new label
                create_body = {
                    'name': label_name,
                    'color': config['color'],
                    'messageListVisibility': config['visibility']['messageListVisibility'],
                    'labelListVisibility': config['visibility']['labelListVisibility']
                }
                
                created_label = self.service.users().labels().create(
                    userId='me',
                    body=create_body
                ).execute()
                
                return True, 'created', f"Created: {label_name}"
                
        except Exception as e:
            return False, 'error', f"Error with {config['name']}: {str(e)}"
    
    def _is_our_label(self, key: str, existing_name: str, label_obj: Dict) -> bool:
        """Check if an existing label matches our label"""
        existing_lower = existing_name.lower()
        
        # Skip system labels for our custom SPAM
        if key == 'spam' and label_obj.get('type') == 'system':
            return False
        
        # Match patterns for our labels
        if key == 'to do':
            return 'to do' in existing_lower or 'todo' in existing_lower or '📋' in existing_name
        elif key == 'awaiting reply':
            return 'awaiting' in existing_lower and 'reply' in existing_lower or '⏳' in existing_name
        elif key == 'fyi':
            return existing_lower == 'fyi' or 'ℹ️' in existing_name
        elif key == 'done':
            return existing_lower == 'done' or '✅' in existing_name
        elif key == 'spam':
            return ('spam' in existing_lower or '🗑️' in existing_name) and label_obj.get('type') != 'system'
        elif key == 'history':
            return 'history' in existing_lower or '📜' in existing_name
        
        return False
    
    def setup_all_labels(self) -> Dict:
        """Setup all required labels"""
        results = {
            'created': 0,
            'updated': 0,
            'errors': 0,
            'actions': [],
            'final_labels': {}
        }
        
        print("🏷️ Setting up all required labels...")
        
        for key, config in self.REQUIRED_LABELS.items():
            success, action, message = self.create_or_update_label(key, config)
            
            if success:
                if action == 'created':
                    results['created'] += 1
                    print(f"✅ {message}")
                elif action == 'updated':
                    results['updated'] += 1
                    print(f"🔄 {message}")
                
                results['final_labels'][key] = config['name']
            else:
                results['errors'] += 1
                print(f"❌ {message}")
            
            results['actions'].append({
                'key': key,
                'action': action,
                'message': message,
                'success': success
            })
        
        return results
    
    def verify_final_setup(self) -> Dict:
        """Verify all our labels are properly set up"""
        # Reload labels after setup
        self._load_existing_labels()
        
        # Check our labels status
        status = self.check_our_labels_status()
        
        verification = {
            'all_labels_found': len(status['missing']) == 0,
            'found_count': status['total_found'],
            'required_count': status['total_required'],
            'missing_labels': status['missing'],
            'found_labels': status['found']
        }
        
        return verification

def authenticate_user(user_email: str) -> Optional[Credentials]:
    """Authenticate user with Gmail"""
    try:
        print(f"🔐 Authenticating {user_email}...")
        
        scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/gmail.labels'
        ]
        
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes)
        credentials = flow.run_local_server(port=0, access_type='offline')
        
        print("✅ Authentication successful!")
        return credentials
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return None

def main():
    """Main label setup function"""
    print("🏷️ Gmail Label Setup - FIXED VERSION")
    print("============================================================")
    
    # Get user email
    default_email = "gaurav@whizmail.ai"
    user_email = input(f"Enter user email (default: {default_email}): ").strip()
    if not user_email:
        user_email = default_email
    
    # Authenticate
    credentials = authenticate_user(user_email)
    if not credentials:
        print("❌ Failed to authenticate. Exiting.")
        return
    
    # Initialize label manager
    label_manager = GmailLabelManager(credentials)
    
    # Check current status
    print(f"\n🔍 Checking current label status for {user_email}...")
    initial_status = label_manager.check_our_labels_status()
    
    print(f"📊 Current Status:")
    print(f"   Required labels: {initial_status['total_required']}")
    print(f"   Found our labels: {initial_status['total_found']}")
    print(f"   Missing our labels: {len(initial_status['missing'])}")
    
    if initial_status['found']:
        print(f"\n🏷️ Found Our Labels:")
        for key, info in initial_status['found'].items():
            label_type = f" ({info['type']})" if info['type'] == 'system' else ""
            print(f"   • {info['name']}{label_type} (key: {key})")
    
    if initial_status['missing']:
        print(f"\n❌ Missing Our Labels: {initial_status['missing']}")
    
    # Ask for confirmation
    if initial_status['total_found'] == initial_status['total_required']:
        print(f"\n✅ All labels already exist!")
        update_anyway = input("🔄 Update labels anyway to ensure proper formatting? (y/N): ").lower()
        if update_anyway != 'y':
            print("👋 Skipping setup")
            return
    else:
        confirm = input(f"\n🚀 Setup/create missing labels for {user_email}? (y/N): ").lower()
        if confirm != 'y':
            print("👋 Setup cancelled")
            return
    
    # Setup labels
    print(f"\n🏷️ Setting up labels...")
    setup_results = label_manager.setup_all_labels()
    
    # Print summary
    print(f"\n📊 Label Setup Summary:")
    print(f"   Created: {setup_results['created']}")
    print(f"   Updated: {setup_results['updated']}")
    print(f"   Total processed: {setup_results['created'] + setup_results['updated']}")
    print(f"   Errors: {setup_results['errors']}")
    
    # Show final labels
    if setup_results['final_labels']:
        print(f"\n🏷️ Our Labels in Gmail:")
        for key, name in setup_results['final_labels'].items():
            print(f"   • {name}")
    
    # Final verification
    print(f"\n🔍 Final verification...")
    verification = label_manager.verify_final_setup()
    
    if verification['all_labels_found']:
        print(f"✅ All {verification['found_count']}/{verification['required_count']} labels are properly set up!")
        print("🎉 Label setup is complete!")
        
        print(f"\n💡 Next steps:")
        print(f"   1. Check Gmail sidebar for all 6 labels")
        print(f"   2. Run email classification: python main.py")
        print(f"   3. Test label application with new emails")
        
    else:
        print(f"⚠️ Setup incomplete!")
        print(f"   Found: {verification['found_count']}/{verification['required_count']}")
        if verification['missing_labels']:
            print(f"   Missing: {verification['missing_labels']}")
    
    return verification['all_labels_found']

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)