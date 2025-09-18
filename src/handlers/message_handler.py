"""Message handler for processing Telegram messages"""
import json
import time
from typing import Dict, Any

from src.models.session import SessionManager
from src.services.telegram_service import TelegramService
from src.services.gemini_service import GeminiService
from src.services.product_service import ProductService
from src.utils.logger import get_logger

logger = get_logger(__name__)

class MessageHandler:
    """Handler for processing Telegram messages"""
    
    def __init__(
        self,
        session_manager: SessionManager,
        telegram_service: TelegramService,
        gemini_service: GeminiService,
        product_service: ProductService
    ):
        self.session_manager = session_manager
        self.telegram = telegram_service
        self.gemini = gemini_service
        self.product = product_service
    
    def handle_message(self, message: Dict[str, Any]) -> None:
        """
        Main message handler
        
        Args:
            message: Telegram message object
        """
        try:
            chat_id = message["chat"]["id"]
            session = self.session_manager.get_session(chat_id)
            
            text = message.get("text", "")
            message_id = message.get("message_id")
            
            # Prevent duplicate message processing
            if message_id and session.last_processed_message_id == message_id:
                logger.info(f"Skipping duplicate message {message_id} for chat {chat_id}")
                return
            
            if message_id:
                session.last_processed_message_id = message_id
            
            # Handle commands
            if text.startswith("/"):
                self._handle_command(chat_id, text, session)
                return
            
            # Handle based on current stage
            stage = session.stage
            logger.info(f"Handling message for chat {chat_id}, stage: {stage}")
            
            if stage == "await_initial_choice":
                # If not a callback and not a command, show welcome
                if not message.get("callback_query"):
                    self.telegram.send_welcome_message(chat_id)
            elif stage.startswith("upload_product_llm"):
                self._handle_product_upload_stage(chat_id, message, session)
            elif stage == "ask_query_llm":
                self._handle_query_stage(chat_id, text, session)
            elif stage == "done":
                self._handle_done_stage(chat_id, text)
            else:
                logger.warning(f"Unknown stage {stage} for chat {chat_id}")
                self.telegram.send_welcome_message(chat_id)
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            # Send generic error message to user
            try:
                self.telegram.send_message(
                    message["chat"]["id"],
                    "I encountered an error processing your message. Please try again or use /restart to start over."
                )
            except:
                pass
    
    def _handle_command(self, chat_id: int, text: str, session) -> None:
        """Handle bot commands"""
        if text.startswith("/start") or text.startswith("/restart"):
            session.reset()
            self.telegram.send_welcome_message(chat_id)
        elif text.startswith("/status"):
            self._send_status(chat_id, session)
        else:
            self.telegram.send_message(
                chat_id,
                "Unknown command. Available commands: /start, /restart, /status"
            )
    
    def _handle_product_upload_stage(self, chat_id: int, message: Dict[str, Any], session) -> None:
        """Handle product upload flow stages"""
        stage = session.stage
        text = message.get("text", "")
        
        if stage == "upload_product_llm_image":
            self._handle_image_stage(chat_id, message, session)
        elif stage == "upload_product_llm_name":
            self._handle_name_stage(chat_id, text, session)
        elif stage == "upload_product_llm_price":
            self._handle_price_stage(chat_id, text, session)
        elif stage == "upload_product_llm_specs":
            self._handle_specs_stage(chat_id, text, session)
    
    def _handle_image_stage(self, chat_id: int, message: Dict[str, Any], session) -> None:
        """Handle image upload stage"""
        file_id = self.product.extract_file_id_from_message(message)
        
        if file_id:
            success, error_msg = self.product.handle_image_upload(file_id, chat_id, session)
            
            if success:
                session.stage = "upload_product_llm_name"
                self.telegram.send_message(chat_id, "Great! I've received your product image.")
                self.telegram.send_skip_keyboard(
                    chat_id,
                    "Now, please provide the *product name*. If you don't have an idea, you can skip this step.",
                    "skip_name"
                )
            else:
                self.telegram.send_message(chat_id, error_msg or "There was an issue with your image. Please try again.")
        else:
            self.telegram.send_message(chat_id, "Please upload a product image to get started.")
    
    def _handle_name_stage(self, chat_id: int, text: str, session) -> None:
        """Handle product name input stage"""
        if text:
            session.data.product_name = text
            session.stage = "upload_product_llm_price"
            self.telegram.send_skip_keyboard(
                chat_id,
                "Thank you! Now please provide the *product price*. If you're unsure, you can skip this step.",
                "skip_price"
            )
    
    def _handle_price_stage(self, chat_id: int, text: str, session) -> None:
        """Handle product price input stage"""
        if text:
            session.data.price = text
            session.stage = "upload_product_llm_specs"
            self.product.start_specification_questions(chat_id, session, "Perfect! ")
    
    def _handle_specs_stage(self, chat_id: int, text: str, session) -> None:
        """Handle specifications input stage"""
        if not text:
            return
        
        # Process the specification answer
        has_more = self.product.process_specification_answer(chat_id, session, text)
        
        if not has_more:
            # All specifications collected, finalize product
            self._finalize_product_upload(chat_id, session)
    
    def _handle_query_stage(self, chat_id: int, text: str, session) -> None:
        """Handle query input stage"""
        if text:
            self.telegram.send_message(
                chat_id,
                f"Thank you for your query: '{text}'. I'm processing it now. (This feature is under development!)"
            )
            session.stage = "done"
            session.llm_history = []
            self.telegram.send_welcome_message(chat_id)
        else:
            self.telegram.send_message(chat_id, "Please type your query.")
    
    def _handle_done_stage(self, chat_id: int, text: str) -> None:
        """Handle done stage"""
        if not text.startswith("/"):
            self.telegram.send_message(
                chat_id,
                "I'm done with the current task. Use the buttons below or type /restart to begin again."
            )
            self.telegram.send_welcome_message(chat_id)
    
    def _finalize_product_upload(self, chat_id: int, session) -> None:
        """Finalize product upload process"""
        product = self.product.finalize_product(chat_id, session)
        
        if product:
            session.stage = "done"
            session.llm_history = []
            self.product.send_product_summary(chat_id, product)
        else:
            self.telegram.send_message(chat_id, "Error: Failed to process product. Please start again.")
            session.reset()
            self.telegram.send_welcome_message(chat_id)
    
    def _send_status(self, chat_id: int, session) -> None:
        """Send session status information"""
        try:
            llm_hist_display = json.dumps(session.llm_history, indent=2, ensure_ascii=False)
            llm_hist_display = (llm_hist_display[:1000] + '...') if len(llm_hist_display) > 1000 else llm_hist_display
            
            data_dict = {
                "product_name": session.data.product_name,
                "price": session.data.price,
                "specifications": session.data.specifications,
                "local_image_path": session.data.local_image_path,
                "current_spec_index": session.data.current_spec_index
            }
            
            status_msg = (
                f"**Session Status**\n\n"
                f"*Stage:* {session.stage}\n"
                f"*Data:* {json.dumps(data_dict, indent=2)}\n\n"
                f"*LLM History:* {llm_hist_display}\n\n"
                f"*Last interaction:* {time.ctime(session.last_interaction_time)}"
            )
            
            self.telegram.send_message(chat_id, status_msg)
        except Exception as e:
            logger.error(f"Error sending status: {e}")
            self.telegram.send_message(chat_id, "Error retrieving status information.")
