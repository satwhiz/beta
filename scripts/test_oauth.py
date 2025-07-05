# test_oauth.py - Simple OAuth test
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

def test_oauth():
    """Test OAuth flow independently"""
    print("🔐 Testing OAuth Flow")
    print("=" * 30)
    
    try:
        # Gmail readonly scope
        scopes = ['https://www.googleapis.com/auth/gmail.readonly']
        
        # Create flow
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', scopes
        )
        
        print("Starting OAuth flow...")
        print("This will open a browser window.")
        print("Please sign in as: gaurav@whizmail.ai")
        
        input("Press Enter to continue...")
        
        # Run local server
        credentials = flow.run_local_server(
            port=8080,
            access_type='offline'
        )
        
        print("✅ Authentication successful!")
        print(f"Access token: {credentials.token[:20]}...")
        print(f"Refresh token: {credentials.refresh_token[:20] if credentials.refresh_token else 'None'}...")
        
        # Test Gmail API
        print("\n📧 Testing Gmail API...")
        service = build('gmail', 'v1', credentials=credentials)
        
        # Get profile
        profile = service.users().getProfile(userId='me').execute()
        print(f"✅ Connected to Gmail for: {profile['emailAddress']}")
        print(f"Total messages: {profile['messagesTotal']}")
        
        # Get a few messages
        results = service.users().messages().list(userId='me', maxResults=5).execute()
        messages = results.get('messages', [])
        print(f"✅ Can access {len(messages)} recent messages")
        
        return True
        
    except Exception as e:
        print(f"❌ OAuth test failed: {e}")
        return False

if __name__ == "__main__":
    test_oauth()