"""Callback query handler for processing inline keyboard interactions"""
from typing import Dict, Any, List

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
            # New AI suggestion handlers
            elif callback_data.startswith("select_name_"):
                self._handle_select_name(chat_id, session, callback_data, message_id)
            elif callback_data == "custom_name":
                self._handle_custom_name(chat_id, session, message_id)
            elif callback_data.startswith("select_spec_"):
                self._handle_select_spec(chat_id, session, callback_data, message_id)
            elif callback_data.startswith("custom_spec_"):
                self._handle_custom_spec(chat_id, session, callback_data, message_id)
            else:
                logger.warning(f"Unknown callback data: {callback_data}")
                
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
    
    def _handle_upload_product(self, chat_id: int, session, message_id: int) -> None:
        """Handle 'Upload Product' button click"""
        # Preserve telegram_user_id across session reset
        telegram_user_id = session.data.telegram_user_id
        
        session.reset()
        session.stage = "upload_product_llm_image"
        
        # Restore telegram_user_id after reset
        if telegram_user_id:
            session.data.telegram_user_id = telegram_user_id
        else:
            pass # No telegram_user_id to preserve
        
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
        logger.info(f"CallbackHandler._finalize_product_upload called for chat {chat_id}")
        logger.info(f"📊 Current session stage: {session.stage}")
        logger.info(f"🌐 Session cloud_image_url: {session.data.cloud_image_url}")
        
        # Get telegram_user_id from session data
        telegram_user_id = session.data.telegram_user_id
        
        if not telegram_user_id:
            logger.error(f"❌ No telegram_user_id found in session for chat {chat_id}")
            self.telegram.send_message(chat_id, "Error: Authentication issue. Please restart with /restart.")
            session.reset()
            return
        
        product = self.product.finalize_product(chat_id, telegram_user_id, session)
        
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
    
    def _handle_select_name(self, chat_id: int, session, callback_data: str, message_id: int) -> None:
        """Handle selection of AI-suggested product name"""
        try:
            # Extract index from callback_data: "select_name_0", "select_name_1", etc.
            index = int(callback_data.split("_")[-1])
            
            if 0 <= index < len(session.data.name_suggestions):
                selected_name = session.data.name_suggestions[index]
                session.data.product_name = selected_name
                
                # Move to price stage
                session.stage = "upload_product_llm_price"
                self.telegram.send_skip_keyboard(
                    chat_id,
                    f"Perfect! Product name: *{selected_name}*\n\nNow please provide the *product price*:",
                    "skip_price"
                )
                
                # Delete the suggestion message
                self.telegram.delete_message(chat_id, message_id)
            else:
                logger.error(f"Invalid name suggestion index: {index}")
                
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing name selection callback: {e}")
    
    def _handle_custom_name(self, chat_id: int, session, message_id: int) -> None:
        """Handle request for custom product name"""
        session.stage = "upload_product_llm_name_suggestions"  # Stay in suggestions stage to handle text input
        
        self.telegram.send_message(
            chat_id,
            "Please enter your custom product name:"
        )
        
        # Delete the suggestion message
        self.telegram.delete_message(chat_id, message_id)
    
    def _handle_select_spec(self, chat_id: int, session, callback_data: str, message_id: int) -> None:
        """Handle selection of AI-suggested specification"""
        try:
            # Extract spec_key and index from callback_data: "select_spec_material_0" or "select_spec_craft_style_0"
            # Handle spec keys that contain underscores by finding the last underscore for the index
            parts = callback_data.split("_")
            # The format is: select_spec_{spec_key}_{index}
            # So we need everything from index 2 to -1 as spec_key, and the last part as index
            spec_key = "_".join(parts[2:-1])  # Join all parts except the first two and last one
            index = int(parts[-1])  # Last part is always the index
            
            if (spec_key in session.data.spec_suggestions and 
                0 <= index < len(session.data.spec_suggestions[spec_key]["suggestions"])):
                
                selected_value = session.data.spec_suggestions[spec_key]["suggestions"][index]
                session.data.specifications[spec_key] = selected_value
                
                # Move to next specification or finish
                from src.handlers.message_handler import MessageHandler
                # We need access to message handler methods, but we can't import it directly due to circular imports
                # So we'll implement the logic here
                session.data.current_spec_index += 1
                spec_keys = list(session.data.spec_suggestions.keys())
                
                if session.data.current_spec_index < len(spec_keys):
                    # Show next specification
                    next_spec_key = spec_keys[session.data.current_spec_index]
                    next_spec_data = session.data.spec_suggestions[next_spec_key]
                    session.data.current_spec_key = next_spec_key
                    
                    self._show_spec_suggestions(
                        chat_id,
                        next_spec_key,
                        next_spec_data["question"],
                        next_spec_data["suggestions"],
                        session
                    )
                else:
                    # All specifications completed, finalize product
                    self.telegram.send_message(chat_id, "✅ Thanks for the information. Your product is being updated!")
                    self._finalize_product_upload(chat_id, session)
                
                # Delete the suggestion message
                self.telegram.delete_message(chat_id, message_id)
            else:
                logger.error(f"Invalid spec suggestion: {spec_key}, index: {index}")
                
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing spec selection callback: {e}")
    
    def _handle_custom_spec(self, chat_id: int, session, callback_data: str, message_id: int) -> None:
        """Handle request for custom specification answer"""
        try:
            # Extract spec_key from callback_data: "custom_spec_material" or "custom_spec_craft_style"
            # Handle spec keys that contain underscores
            parts = callback_data.split("_")
            # The format is: custom_spec_{spec_key}
            # So we need everything from index 2 onwards as spec_key
            spec_key = "_".join(parts[2:])  # Join all parts after "custom_spec"
            session.data.current_spec_key = spec_key
            session.stage = "upload_product_llm_specs_suggestions"  # Stay in suggestions stage to handle text input
            
            question = session.data.spec_suggestions.get(spec_key, {}).get("question", f"Enter value for {spec_key}")
            self.telegram.send_message(
                chat_id,
                f"Please enter your custom answer for:\n*{question}*"
            )
            
            # Delete the suggestion message
            self.telegram.delete_message(chat_id, message_id)
            
        except Exception as e:
            logger.error(f"Error handling custom spec callback: {e}")
    
    def _show_spec_suggestions(self, chat_id: int, spec_key: str, question: str, suggestions: List[str], session) -> None:
        """Show AI specification suggestions as inline keyboard"""
        import json
        
        # Create inline keyboard with spec suggestions
        keyboard_buttons = []
        for i, suggestion in enumerate(suggestions):
            keyboard_buttons.append([{"text": suggestion, "callback_data": f"select_spec_{spec_key}_{i}"}])
        
        # Add option for custom answer and skip
        keyboard_buttons.append([{"text": "✏️ Enter Custom Answer", "callback_data": f"custom_spec_{spec_key}"}])
        keyboard_buttons.append([{"text": "⏭️ Skip This", "callback_data": f"skip_spec_{spec_key}"}])
        
        keyboard = {"inline_keyboard": keyboard_buttons}
        
        # Get current progress info from session
        current_index = getattr(session.data, 'current_spec_index', 0) + 1
        total_questions = len(getattr(session.data, 'spec_suggestions', {}))
        
        self.telegram.send_message(
            chat_id,
            f"🤖 *Question {current_index}/{total_questions}*\n\n*{question}*\n\nChoose an AI suggestion or enter your own:",
            reply_markup=json.dumps(keyboard)
        )
