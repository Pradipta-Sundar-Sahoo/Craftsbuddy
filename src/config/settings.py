"""Configuration settings for CraftBuddy bot"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BotConfig:
    """Bot configuration class"""
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_API_BASE: str = "https://api.telegram.org/bot"
    TELEGRAM_FILE_BASE: str = "https://api.telegram.org/file/bot"
    
    # Gemini AI Configuration
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = "gemini-1.5-flash"
    USE_GEMINI: bool = bool(GEMINI_API_KEY)
    
    # Session Configuration
    CONTEXT_TIMEOUT_SECONDS: int = 15 * 60  # 15 minutes
    
    # Google Cloud Storage Configuration (Required)
    GCS_BUCKET_NAME: Optional[str] = os.getenv("GCS_BUCKET_NAME")
    GCS_CREDENTIALS_PATH: Optional[str] = os.getenv("GCS_CREDENTIALS_PATH")
    USE_GCS: bool = bool(GCS_BUCKET_NAME)
    
    # Bot Instance Configuration
    BOT_POLLING_TIMEOUT: int = 25
    MAX_PROCESSED_UPDATES: int = 1000
    
    # Validation
    def validate(self) -> bool:
        """Validate required configuration"""
        if not self.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        return True
    
    @property
    def telegram_base_url(self) -> str:
        """Get Telegram API base URL"""
        return f"{self.TELEGRAM_API_BASE}{self.TELEGRAM_BOT_TOKEN}"
    
    @property
    def telegram_file_url(self) -> str:
        """Get Telegram file API base URL"""
        return f"{self.TELEGRAM_FILE_BASE}{self.TELEGRAM_BOT_TOKEN}"

# Global configuration instance
config = BotConfig()
