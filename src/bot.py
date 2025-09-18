"""Main bot class for CraftBuddy Telegram Bot"""
import os
import random
import time
import traceback
from typing import Set
import atexit

from src.config.settings import config
from src.models.session import SessionManager
from src.services.telegram_service import TelegramService
from src.services.gemini_service import GeminiService
from src.services.product_service import ProductService
from src.handlers.message_handler import MessageHandler
from src.handlers.callback_handler import CallbackHandler
from src.utils.logger import get_logger, setup_logger

class CraftBuddyBot:
    """Main bot class that orchestrates all components"""
    
    def __init__(self):
        # Setup logging
        self.logger = setup_logger("craftbuddy_bot", "INFO", "bot.log")
        
        # Validate configuration
        try:
            config.validate()
        except ValueError as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise
        
        # Initialize bot instance ID
        self.instance_id = random.randint(1000, 9999)
        self.logger.info(f"Bot instance {self.instance_id} initializing...")
        
        # Instance control
        self.lockfile_path = "bot.lock"
        self._acquire_lock()
        
        # Initialize processed updates tracking
        self.processed_updates: Set[int] = set()
        
        # Initialize components
        self._initialize_components()
        
        # Clear any existing webhooks before starting polling
        self._clear_webhooks()
        
        self.logger.info(f"Bot instance {self.instance_id} initialized successfully")
    
    def _initialize_components(self) -> None:
        """Initialize all bot components"""
        # Initialize session manager
        self.session_manager = SessionManager(config.CONTEXT_TIMEOUT_SECONDS)
        
        # Initialize services
        self.telegram_service = TelegramService()
        self.gemini_service = GeminiService()
        self.product_service = ProductService(self.telegram_service, self.gemini_service)
        
        # Initialize handlers
        self.message_handler = MessageHandler(
            self.session_manager,
            self.telegram_service,
            self.gemini_service,
            self.product_service
        )
        
        self.callback_handler = CallbackHandler(
            self.session_manager,
            self.telegram_service,
            self.product_service
        )
        
        self.logger.info("All bot components initialized")
    
    def _acquire_lock(self) -> None:
        """Acquire instance lock to prevent multiple bot instances"""
        if os.path.exists(self.lockfile_path):
            self.logger.error(f"Another bot instance is already running (lockfile: {self.lockfile_path})")
            self.logger.error("Please stop the other instance or remove the lockfile if it's stale")
            raise RuntimeError("Another bot instance is already running")
        
        try:
            # Create lockfile
            with open(self.lockfile_path, 'w') as f:
                f.write(f"{self.instance_id}\n{time.time()}")
            
            # Register cleanup on exit
            atexit.register(self._release_lock)
            
            self.logger.info(f"Acquired instance lock: {self.lockfile_path}")
        except Exception as e:
            self.logger.error(f"Failed to acquire lock: {e}")
            raise
    
    def _release_lock(self) -> None:
        """Release instance lock"""
        try:
            if os.path.exists(self.lockfile_path):
                os.remove(self.lockfile_path)
                self.logger.info(f"Released instance lock: {self.lockfile_path}")
        except Exception as e:
            self.logger.warning(f"Failed to release lock: {e}")
    
    def _clear_webhooks(self) -> None:
        """Clear any existing webhooks to ensure polling can work"""
        try:
            self.logger.info("Clearing any existing webhooks...")
            success = self.telegram_service.delete_webhook()
            if success:
                self.logger.info("Successfully cleared webhooks")
            else:
                self.logger.warning("Failed to clear webhooks, but continuing...")
        except Exception as e:
            self.logger.warning(f"Error clearing webhooks: {e}, but continuing...")

    def run(self) -> None:
        """Start the bot with long polling"""
        self.logger.info(f"Bot instance {self.instance_id} starting with long polling...")
        offset = None
        
        try:
            while True:
                try:
                    # Get updates from Telegram
                    updates_response = self.telegram_service.get_updates(
                        offset=offset,
                        timeout=config.BOT_POLLING_TIMEOUT
                    )
                    
                    updates = updates_response.get("result", [])
                    
                    for update in updates:
                        try:
                            self._process_update(update)
                            offset = update["update_id"] + 1
                        except Exception as e:
                            self.logger.error(f"Error processing update {update.get('update_id', 'unknown')}: {e}")
                            traceback.print_exc()
                            # Continue processing other updates
                            continue
                    
                    # Periodic cleanup
                    self._periodic_cleanup()
                    
                except KeyboardInterrupt:
                    self.logger.info("Bot stopped by user (Ctrl+C)")
                    break
                except Exception as e:
                    self.logger.error(f"Error in main loop: {e}")
                    traceback.print_exc()
                    time.sleep(2)  # Wait before retrying
                    
        except Exception as e:
            self.logger.error(f"Fatal error in bot: {e}")
            traceback.print_exc()
            raise
        finally:
            self.logger.info(f"Bot instance {self.instance_id} shutting down...")
            self._release_lock()
    
    def _process_update(self, update: dict) -> None:
        """
        Process a single update from Telegram
        
        Args:
            update: Update object from Telegram
        """
        update_id = update.get("update_id")
        
        # Skip duplicate updates
        if update_id in self.processed_updates:
            self.logger.debug(f"Skipping duplicate update {update_id}")
            return
        
        # Mark update as processed
        self.processed_updates.add(update_id)
        
        # Process based on update type
        if "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            
            # Ensure session exists before processing
            self.session_manager.get_session(chat_id)
            self.message_handler.handle_message(message)
            
        elif "callback_query" in update:
            callback_query = update["callback_query"]
            chat_id = callback_query["message"]["chat"]["id"]
            
            # Ensure session exists before processing
            self.session_manager.get_session(chat_id)
            self.callback_handler.handle_callback_query(callback_query)
        else:
            self.logger.debug(f"Unhandled update type: {list(update.keys())}")
    
    def _periodic_cleanup(self) -> None:
        """Perform periodic cleanup tasks"""
        # Clean old processed updates (keep only last 1000)
        if len(self.processed_updates) > config.MAX_PROCESSED_UPDATES:
            self.logger.info("Cleaning old processed updates")
            self.processed_updates.clear()
        
        # Clean expired sessions
        expired_count = self.session_manager.cleanup_expired_sessions()
        if expired_count > 0:
            self.logger.info(f"Cleaned up {expired_count} expired sessions")
    
    def stop(self) -> None:
        """Stop the bot gracefully"""
        self.logger.info(f"Bot instance {self.instance_id} stopping...")
        self._release_lock()
        # Add any cleanup code here if needed
        
    def get_stats(self) -> dict:
        """Get bot statistics"""
        return {
            "instance_id": self.instance_id,
            "active_sessions": len(self.session_manager.sessions),
            "processed_updates_count": len(self.processed_updates),
            "gemini_enabled": self.gemini_service.enabled,
        }
