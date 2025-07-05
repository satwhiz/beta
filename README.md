# Email Agent System

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
