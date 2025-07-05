# utils/logging.py - Minimal logging setup
import sys
from loguru import logger

def setup_logging():
    """Setup basic logging configuration"""
    # Remove default logger
    logger.remove()
    
    # Add console logging
    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="INFO"
    )
    
    # Add file logging (optional)
    try:
        import os
        os.makedirs("logs", exist_ok=True)
        logger.add(
            "logs/email_agent.log",
            rotation="1 day",
            retention="7 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
            level="DEBUG"
        )
    except Exception:
        # If file logging fails, just continue with console logging
        pass