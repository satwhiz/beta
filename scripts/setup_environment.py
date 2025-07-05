# scripts/setup_environment.py
import os
import sys
from pathlib import Path

def create_directory_structure():
    """Create the complete directory structure"""
    print("📁 Creating directory structure...")
    
    directories = [
        "config",
        "models", 
        "agents",
        "tools",
        "utils",
        "workflows",
        "push_notifications",
        "push_notifications/monitoring",
        "tests",
        "logs",
        "scripts",
        "docs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"  ✅ Created: {directory}/")
    
    print("✅ Directory structure created!")

def create_init_files():
    """Create __init__.py files for Python packages"""
    print("\n📄 Creating __init__.py files...")
    
    init_dirs = [
        "config",
        "models",
        "agents", 
        "tools",
        "utils",
        "workflows",
        "push_notifications",
        "push_notifications/monitoring",
        "tests",
        "scripts"
    ]
    
    for directory in init_dirs:
        init_file = Path(directory) / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# Package initialization\n")
            print(f"  ✅ Created: {init_file}")
    
    print("✅ __init__.py files created!")

def create_env_template():
    """Create .env template file"""
    print("\n🔧 Creating .env template...")
    
    env_content = """# Email Agent System Environment Variables

# API Keys
OPENAI_API_KEY=your_openai_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here

# Google Cloud (for push notifications)  
GOOGLE_CLOUD_PROJECT_ID=robust-metrics-465003-n0
PUBSUB_TOPIC_NAME=gmail-notifications
PUBSUB_SUBSCRIPTION_NAME=gmail-notifications-sub

# Webhook Configuration
WEBHOOK_URL=https://your-domain.com/gmail-webhook
WEBHOOK_SECRET=your-secure-webhook-secret

# Flask Server Configuration
FLASK_PORT=8080
FLASK_HOST=0.0.0.0

# Email Processing Settings
EMAIL_FETCH_LIMIT=100
HISTORY_DAYS_THRESHOLD=5

# Pinecone Configuration
PINECONE_ENVIRONMENT=us-west1-gcp
PINECONE_INDEX_NAME=email-context

# Google OAuth (optional - usually in credentials.json)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Development Settings
DEBUG=false
LOG_LEVEL=INFO
"""
    
    env_file = Path(".env")
    if not env_file.exists():
        env_file.write_text(env_content)
        print("  ✅ Created: .env template")
        print("  📝 Please update .env with your actual API keys")
    else:
        print("  ℹ️  .env file already exists")

def create_requirements_files():
    """Create requirements files"""
    print("\n📦 Creating requirements files...")
    
    # Basic requirements
    basic_requirements = """# Basic Email Agent System Requirements
agno
openai
google-auth
google-auth-oauthlib
google-auth-httplib2
google-api-python-client
pydantic
python-dotenv
python-dateutil
loguru
nltk
"""
    
    # Push notification requirements
    push_requirements = """# Additional Push Notification Requirements
flask
google-cloud-pubsub
google-cloud-core
gunicorn
requests
threading
"""
    
    # Write requirements files
    Path("requirements.txt").write_text(basic_requirements)
    Path("requirements_push.txt").write_text(push_requirements)
    
    print("  ✅ Created: requirements.txt")
    print("  ✅ Created: requirements_push.txt")

def create_gitignore():
    """Create .gitignore file"""
    print("\n🙈 Creating .gitignore...")
    
    gitignore_content = """# Environment variables
.env
.env.local
.env.development
.env.production

# API Keys and Credentials
credentials.json
token.json
service-account-key.json

# User data
users.csv
*.db

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs
logs/
*.log

# OS
.DS_Store
Thumbs.db

# Flask
instance/
.webassets-cache

# Testing
.coverage
.pytest_cache/
htmlcov/

# Temporary files
*.tmp
*.temp
"""
    
    gitignore_file = Path(".gitignore")
    if not gitignore_file.exists():
        gitignore_file.write_text(gitignore_content)
        print("  ✅ Created: .gitignore")
    else:
        print("  ℹ️  .gitignore already exists")

def create_readme():
    """Create README.md file"""
    print("\n📖 Creating README.md...")
    
    readme_content = """# Email Agent System

Intelligent email management system with thread-based classification and real-time push notifications.

## Features

- 🧵 **Thread-based Classification**: Analyzes entire email conversations
- 🔔 **Push Notifications**: Real-time email processing as emails arrive  
- 🏷️ **Smart Labels**: AI-powered email categorization
- 📊 **User Management**: Multi-user support with isolated data
- 🚀 **Scalable**: From local testing to production deployment

## Quick Start

### 1. Setup Environment
```bash
# Run setup script
python3 scripts/setup_environment.py

# Install dependencies  
pip install -r requirements.txt
pip install -r requirements_push.txt
```

### 2. Configure API Keys
Edit `.env` file with your API keys:
- OpenAI API key
- Google Cloud credentials
- Pinecone API key (optional)

### 3. Add Google Credentials
Place your `credentials.json` file in the root directory.

### 4. Run the System

**Thread-based Classification:**
```bash
python3 main.py
```

**Simple Push Notifications:**
```bash
python3 push_notifications/simple_webhook_server.py
```

**Full Production System:**
```bash
python3 push_notifications/setup_push_notifications.py
python3 push_notifications/push_notification_system.py
```

## Testing

```bash
# Test thread classifier
python3 tests/test_thread_classifier.py

# Test push notifications
python3 tests/test_push_notifications.py

# Run all tests
python3 scripts/run_tests.py
```

## Documentation

- [Push Notifications Guide](docs/push_notifications.md)
- [API Reference](docs/api_reference.md)

## License

MIT License
"""
    
    readme_file = Path("README.md")
    if not readme_file.exists():
        readme_file.write_text(readme_content)
        print("  ✅ Created: README.md")
    else:
        print("  ℹ️  README.md already exists")

def verify_setup():
    """Verify the setup is complete"""
    print("\n🔍 Verifying setup...")
    
    required_files = [
        ".env",
        "requirements.txt", 
        "requirements_push.txt",
        ".gitignore",
        "README.md"
    ]
    
    required_dirs = [
        "config",
        "models",
        "agents",
        "tools", 
        "utils",
        "workflows",
        "push_notifications",
        "tests",
        "logs",
        "scripts",
        "docs"
    ]
    
    missing_files = []
    missing_dirs = []
    
    # Check files
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
        else:
            print(f"  ✅ {file}")
    
    # Check directories
    for directory in required_dirs:
        if not Path(directory).exists():
            missing_dirs.append(directory)
        else:
            print(f"  ✅ {directory}/")
    
    if missing_files:
        print(f"  ❌ Missing files: {', '.join(missing_files)}")
    
    if missing_dirs:
        print(f"  ❌ Missing directories: {', '.join(missing_dirs)}")
    
    if not missing_files and not missing_dirs:
        print("✅ Setup verification complete!")
        return True
    else:
        print("⚠️  Setup incomplete!")
        return False

def print_next_steps():
    """Print next steps for the user"""
    print(f"\n{'='*50}")
    print("🎉 ENVIRONMENT SETUP COMPLETE!")
    print(f"{'='*50}")
    
    print("\n📋 Next Steps:")
    print("1. 🔑 Update .env file with your API keys:")
    print("   - OPENAI_API_KEY")
    print("   - PINECONE_API_KEY (optional)")
    print("   - Google Cloud settings (for push notifications)")
    
    print("\n2. 📄 Add credentials.json file:")
    print("   - Download from Google Cloud Console")
    print("   - Place in root directory")
    
    print("\n3. 📦 Install dependencies:")
    print("   pip install -r requirements.txt")
    print("   pip install -r requirements_push.txt")
    
    print("\n4. 🧪 Test the system:")
    print("   python3 tests/test_thread_classifier.py")
    
    print("\n5. 🚀 Run the system:")
    print("   # Thread-based classification:")
    print("   python3 main.py")
    print("")
    print("   # Simple push notifications:")
    print("   python3 push_notifications/simple_webhook_server.py")
    
    print(f"\n📖 Documentation:")
    print("   • README.md - Main documentation") 
    print("   • docs/ - Detailed guides")
    print("   • tests/ - Example usage")

def main():
    """Main setup function"""
    print("🚀 Email Agent System - Environment Setup")
    print("=" * 50)
    
    try:
        # Create directory structure
        create_directory_structure()
        
        # Create __init__.py files
        create_init_files()
        
        # Create configuration files
        create_env_template()
        create_requirements_files()
        create_gitignore() 
        create_readme()
        
        # Verify setup
        setup_complete = verify_setup()
        
        if setup_complete:
            print_next_steps()
        else:
            print("\n❌ Setup failed. Please check the errors above.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()