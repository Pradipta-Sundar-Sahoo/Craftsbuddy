"""Telegram API service for CraftBuddy bot"""
import json
from typing import Dict, List, Optional, Any
import httpx

from src.config.settings import config
from src.utils.logger import get_logger
from src.utils.file_utils import sanitize_file_path

logger = get_logger(__name__)

class TelegramService:
    """Service for Telegram API interactions"""
    
    def __init__(self):
        self.base_url = config.telegram_base_url
        self.file_base_url = config.telegram_file_url
        self.timeout = config.BOT_POLLING_TIMEOUT
    
    def get_updates(self, offset: Optional[int] = None, timeout: int = 25) -> Dict[str, Any]:
        """
        Get updates from Telegram with retry logic for 409 conflicts
        
        Args:
            offset: Offset for getting updates
            timeout: Timeout for long polling
            
        Returns:
            Updates response from Telegram API
        """
        params = {"timeout": timeout}
        if offset:
            params["offset"] = offset
            
        max_retries = 3
        retry_delay = 2  # Start with 2 seconds
        
        for attempt in range(max_retries):
            try:
                response = httpx.get(
                    f"{self.base_url}/getUpdates",
                    params=params,
                    timeout=timeout + 5
                )
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 409:  # Conflict error
                    if attempt < max_retries - 1:
                        logger.warning(f"409 Conflict detected (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay}s...")
                        # Delete webhook to resolve conflict
                        self.delete_webhook()
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        logger.error("Max retries exceeded for 409 Conflict. Another bot instance may be running.")
                        logger.error("Please stop all other bot instances and try again.")
                        raise e
                else:
                    logger.error(f"HTTP error getting updates: {e}")
                    return {"result": []}
                    
            except httpx.HTTPError as e:
                logger.error(f"HTTP error getting updates: {e}")
                return {"result": []}
                
        return {"result": []}
    
    def send_message(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[str] = None,
        parse_mode: str = "Markdown"
    ) -> Optional[Dict[str, Any]]:
        """
        Send text message to chat
        
        Args:
            chat_id: Telegram chat ID
            text: Message text
            reply_to_message_id: Optional message ID to reply to
            reply_markup: Optional keyboard markup (JSON string)
            parse_mode: Message parse mode
            
        Returns:
            Response from Telegram API or None if failed
        """
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
        if reply_markup:
            payload["reply_markup"] = reply_markup
        
        try:
            logger.info(f"Sending message to {chat_id}: {text[:100]}...")
            response = httpx.post(
                f"{self.base_url}/sendMessage",
                json=payload,
                timeout=20
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending message: {e}")
            return None
    
    def send_welcome_message(self, chat_id: int) -> None:
        """Send welcome message with inline keyboard"""
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "Upload a Product", "callback_data": "upload_product"},
                    {"text": "Ask Queries", "callback_data": "ask_queries"}
                ]
            ]
        }
        
        self.send_message(
            chat_id,
            "*Welcome to CraftBuddy seller assistant bot!*\n\nHow may I help you today?",
            reply_markup=json.dumps(keyboard)
        )
    
    def send_skip_keyboard(
        self,
        chat_id: int,
        message: str,
        skip_callback: str
    ) -> None:
        """Send message with skip button"""
        keyboard = {
            "inline_keyboard": [
                [{"text": "Skip", "callback_data": skip_callback}]
            ]
        }
        
        self.send_message(
            chat_id,
            message,
            reply_markup=json.dumps(keyboard)
        )
    
    def get_file_info(self, file_id: str) -> Optional[str]:
        """
        Get file path from Telegram API
        
        Args:
            file_id: Telegram file ID
            
        Returns:
            File path or None if failed
        """
        try:
            response = httpx.get(
                f"{self.base_url}/getFile",
                params={"file_id": file_id},
                timeout=15  # Reduced from 20 to 15 seconds
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("ok"):
                file_path = result["result"]["file_path"]
                return file_path
            else:
                logger.error(f"get_file_info failed: {result}")
                return None
        except (httpx.HTTPError, KeyError) as e:
            logger.error(f"Error getting file info: {e}")
            return None
    
    def download_file(self, file_path: str) -> Optional[bytes]:
        """
        Download file content from Telegram
        
        Args:
            file_path: File path from Telegram
            
        Returns:
            File content bytes or None if failed
        """
        try:
            sanitized_path = sanitize_file_path(file_path)
            url = f"{self.file_base_url}/{sanitized_path}"
            
            response = httpx.get(url, timeout=45)  # Reduced from 60 to 45 seconds
            response.raise_for_status()
            content_size = len(response.content)
            return response.content
        except httpx.HTTPError as e:
            logger.error(f"Error downloading file content: {e}")
            return None
    
    def delete_webhook(self) -> bool:
        """
        Delete webhook to ensure polling can work
        
        Returns:
            True if successful, False otherwise
        """
        try:
            response = httpx.post(
                f"{self.base_url}/deleteWebhook",
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            if result.get("ok"):
                logger.info("Successfully deleted webhook")
                return True
            else:
                logger.warning(f"Failed to delete webhook: {result}")
                return False
        except httpx.HTTPError as e:
            logger.error(f"HTTP error deleting webhook: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting webhook: {e}")
            return False

    def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None
    ) -> bool:
        """
        Answer callback query
        
        Args:
            callback_query_id: Callback query ID
            text: Optional text to show
            
        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {"callback_query_id": callback_query_id}
            if text:
                payload["text"] = text
                
            response = httpx.post(
                f"{self.base_url}/answerCallbackQuery",
                json=payload,
                timeout=5
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to answer callback query: {e}")
            return False
    
    def delete_message(self, chat_id: int, message_id: int) -> bool:
        """
        Delete message
        
        Args:
            chat_id: Chat ID
            message_id: Message ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = httpx.post(
                f"{self.base_url}/deleteMessage",
                json={"chat_id": chat_id, "message_id": message_id},
                timeout=5
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to delete message: {e}")
            return False
    
    def extract_largest_photo(self, photos: List[Dict]) -> Optional[str]:
        """
        Extract file_id of largest photo from photos array
        
        Args:
            photos: Array of photo objects from Telegram
            
        Returns:
            File ID of largest photo or None
        """
        if not photos:
            return None
            
        try:
            largest_photo = max(photos, key=lambda p: p.get('file_size', 0))
            return largest_photo.get("file_id")
        except (KeyError, ValueError):
            logger.error("Failed to extract largest photo")
            return None
