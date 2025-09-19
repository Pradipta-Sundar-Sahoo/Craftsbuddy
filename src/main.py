"""Main entry point for CraftBuddy Telegram Bot"""
import sys
import os

# Add parent directory to Python path to enable imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bot import CraftBuddyBot
from src.utils.logger import setup_logger

def main():
    """Main entry point"""
    
    # Setup main logger
    logger = setup_logger("craftbuddy_main", "INFO", "main.log")
    
    try:
        
        # Create and run bot
        
        bot = CraftBuddyBot()
        
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    main()
