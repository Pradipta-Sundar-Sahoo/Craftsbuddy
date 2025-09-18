"""Main entry point for CraftBuddy Telegram Bot"""
import sys
import os

from src.bot import CraftBuddyBot
from src.utils.logger import setup_logger

def main():
    """Main entry point"""
    # Setup main logger
    logger = setup_logger("craftbuddy_main", "INFO", "main.log")
    
    try:
        logger.info("Starting CraftBuddy Telegram Bot...")
        
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
