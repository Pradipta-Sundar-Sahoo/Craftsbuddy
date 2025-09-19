"""Callback query handler for processing inline keyboard interactions"""
from typing import Dict, Any

from src.models.session import SessionManager
from src.services.telegram_service import TelegramService
from src.services.product_service import ProductService
from src.utils.logger import get_logger

logger = get_logger(__name__)

class CallbackHandler:
    """Handler for processing callback queries (inline keyboard buttons)"""
    
    def __init__(
        self,
        session_manager: SessionManager,
        telegram_service: TelegramService,
        product_service: ProductService
    ):
        self.session_manager = session_manager
        self.telegram = telegram_service
        self.product = product_service
    
    def handle_callback_query(self, callback_query: Dict[str, Any]) -> None:
        """
        Main callback query handler
        
        Args:
            callback_query: Telegram callback query object
        """
        try:
            chat_id = callback_query["message"]["chat"]["id"]
            callback_data = callback_query["data"]
            callback_query_id = callback_query["id"]
            message_id = callback_query["message"]["message_id"]
            
            session = self.session_manager.get_session(chat_id)
            
            logger.info(f"Handling callback {callback_data} for chat {chat_id}")
            
            # Acknowledge the callback query
            self.telegram.answer_callback_query(callback_query_id)
            
            # Handle based on callback data
            if callback_data == "upload_product":
                self._handle_upload_product(chat_id, session, message_id)
            elif callback_data == "ask_queries":
                self._handle_ask_queries(chat_id, session, message_id)
            elif callback_data == "skip_name":
                self._handle_skip_name(chat_id, session, message_id)
            elif callback_data == "skip_price":
                self._handle_skip_price(chat_id, session, message_id)
            elif callback_data == "skip_specs":
                self._handle_skip_specs(chat_id, session, message_id)
            elif callback_data.startswith("skip_spec_"):
                self._handle_skip_individual_spec(chat_id, session, callback_data, message_id)
            else:
                logger.warning(f"Unknown callback data: {callback_data}")
                
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
    
    def _handle_upload_product(self, chat_id: int, session, message_id: int) -> None:
        """Handle 'Upload Product' button click"""
        session.reset()
        session.stage = "upload_product_llm_image"
        
        self.telegram.send_message(
            chat_id,
            "Let's start by uploading a *product image*. Please send me a photo of your product."
        )
        
        # Delete the original message with buttons
        self.telegram.delete_message(chat_id, message_id)
    
    def _handle_ask_queries(self, chat_id: int, session, message_id: int) -> None:
        """Handle 'Ask Queries' button click"""
        session.reset()
        session.stage = "ask_query_llm"
        
        self.telegram.send_message(chat_id, "Please type your query.")
        
        # Delete the original message with buttons
        self.telegram.delete_message(chat_id, message_id)
    
    def _handle_skip_name(self, chat_id: int, session, message_id: int) -> None:
        """Handle 'Skip' button for product name"""
        session.stage = "upload_product_llm_price"
        
        self.telegram.send_skip_keyboard(
            chat_id,
            "Skipped name. Now please provide the *product price*. If you're unsure, you can skip this step.",
            "skip_price"
        )
        
        # Delete the original message with skip button
        self.telegram.delete_message(chat_id, message_id)
    
    def _handle_skip_price(self, chat_id: int, session, message_id: int) -> None:
        """Handle 'Skip' button for product price"""
        session.stage = "upload_product_llm_specs"
        
        self.product.start_specification_questions(chat_id, session, "Skipped price. ")
        
        # Delete the original message with skip button
        self.telegram.delete_message(chat_id, message_id)
    
    def _handle_skip_specs(self, chat_id: int, session, message_id: int) -> None:
        """Handle 'Skip' button for all specifications (fallback)"""
        self._finalize_product_upload(chat_id, session)
        
        # Delete the original message with skip button
        self.telegram.delete_message(chat_id, message_id)
    
    def _handle_skip_individual_spec(
        self,
        chat_id: int,
        session,
        callback_data: str,
        message_id: int
    ) -> None:
        """Handle 'Skip' button for individual specification"""
        # Extract spec key from callback data (remove "skip_spec_" prefix)
        spec_key = callback_data[10:]
        
        # Skip current specification and move to next
        has_more = self.product.skip_specification_question(chat_id, session, spec_key)
        
        if not has_more:
            # All specifications processed, finalize product
            self._finalize_product_upload(chat_id, session)
        
        # Delete the original message with skip button
        self.telegram.delete_message(chat_id, message_id)
    
    def _finalize_product_upload(self, chat_id: int, session) -> None:
        """Finalize product upload process"""
        logger.info(f"🎯 CallbackHandler._finalize_product_upload called for chat {chat_id}")
        logger.info(f"📊 Current session stage: {session.stage}")
        logger.info(f"🌐 Session cloud_image_url: {session.data.cloud_image_url}")
        
        product = self.product.finalize_product(chat_id, session)
        
        if product:
            logger.info(f"✅ Product finalization successful in callback handler")
            session.stage = "done"
            session.llm_history = []
            self.product.send_product_summary(chat_id, product)
        else:
            logger.error(f"❌ Product finalization failed in callback handler")
            self.telegram.send_message(chat_id, "Error: Failed to process product. Please start again.")
            session.reset()
            self.telegram.send_welcome_message(chat_id)
