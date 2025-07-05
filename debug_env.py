# debug_env.py - Debug environment variable loading
import os
from dotenv import load_dotenv

def debug_env_loading():
    """Debug environment variable loading"""
    print("🔍 Debugging Environment Variable Loading")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = ".env"
    if os.path.exists(env_file):
        print(f"✅ Found .env file: {env_file}")
        
        # Read .env file content
        with open(env_file, 'r') as f:
            content = f.read()
        
        print(f"📄 .env file content (first 200 chars):")
        print(content[:200] + "..." if len(content) > 200 else content)
        
        # Check for OPENAI_API_KEY in file
        if "OPENAI_API_KEY" in content:
            print("✅ OPENAI_API_KEY found in .env file")
        else:
            print("❌ OPENAI_API_KEY not found in .env file")
    else:
        print(f"❌ .env file not found: {env_file}")
        return False
    
    # Try to load .env
    print(f"\n🔄 Loading .env file...")
    result = load_dotenv(env_file)
    print(f"load_dotenv() result: {result}")
    
    # Check environment variables
    print(f"\n🔍 Checking environment variables:")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print(f"✅ OPENAI_API_KEY loaded: {openai_key[:20]}...")
    else:
        print("❌ OPENAI_API_KEY not loaded")
    
    # Check other important vars
    other_vars = [
        "PINECONE_API_KEY",
        "GOOGLE_CLIENT_ID", 
        "EMAIL_FETCH_LIMIT",
        "HISTORY_DAYS_THRESHOLD"
    ]
    
    for var in other_vars:
        value = os.getenv(var)
        if value:
            display_value = value[:20] + "..." if len(value) > 20 else value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: Not loaded")
    
    return openai_key is not None

if __name__ == "__main__":
    debug_env_loading()