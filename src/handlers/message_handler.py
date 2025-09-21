"""Message handler for processing Telegram messages"""
import json
import time
from typing import Dict, Any, List

from src.models.session import SessionManager
from src.services.telegram_service import TelegramService
from src.services.gemini_service import GeminiService
from src.services.product_service import ProductService
from src.services.database_service import DatabaseService
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
        self.db_service = DatabaseService()
    
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
            
            # Handle commands (allow certain commands even without authentication)
            if text.startswith("/"):
                self._handle_command(chat_id, text, session, message)
                return
            
            # Extract telegram user ID from message
            telegram_user_id = message.get("from", {}).get("id")
            if not telegram_user_id:
                logger.warning(f"Could not extract telegram user ID from message for chat {chat_id}")
                self.telegram.send_message(chat_id, "Sorry, there was an error processing your request. Please try again.")
                return
            
            # Handle based on current stage
            stage = session.stage
            logger.info(f"Handling message for chat {chat_id}, stage: {stage}, telegram_user_id: {telegram_user_id}")
            
            if stage == "await_authentication":
                self._handle_authentication_stage(chat_id, telegram_user_id, session)
            elif stage == "await_phone_verification":
                self._handle_phone_verification_stage(chat_id, text, telegram_user_id, session)
            elif stage == "await_initial_choice":
                # If not a callback and not a command, show welcome
                if not message.get("callback_query"):
                    self.telegram.send_welcome_message(chat_id)
            elif stage == "upload_product_llm_name_suggestions":
                self._handle_name_suggestions_stage(chat_id, text, session)
            elif stage == "upload_product_llm_specs_suggestions":
                self._handle_specs_suggestions_stage(chat_id, text, session)
            elif stage.startswith("upload_product_llm"):
                self._handle_product_upload_stage(chat_id, message, session)
            elif stage == "ask_query_llm":
                self._handle_query_stage(chat_id, text, session)
            elif stage == "done":
                self._handle_done_stage(chat_id, text)
            else:
                logger.warning(f"Unknown stage {stage} for chat {chat_id}")
                session.stage = "await_authentication"
                self._handle_authentication_stage(chat_id, telegram_user_id, session)
                
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
    
    def _handle_command(self, chat_id: int, text: str, session, message: Dict[str, Any]) -> None:
        """Handle bot commands"""
        if text.startswith("/start") or text.startswith("/restart"):
            session.reset()
            # Extract telegram user ID and check authentication
            telegram_user_id = message.get("from", {}).get("id")
            if telegram_user_id:
                self._handle_authentication_stage(chat_id, telegram_user_id, session)
            else:
                self.telegram.send_message(chat_id, "Sorry, there was an error processing your request. Please try again.")
        elif text.startswith("/status"):
            self._send_status(chat_id, session)
        else:
            self.telegram.send_message(
                chat_id,
                "Unknown command. Available commands: /start, /restart, /status"
            )
    
    def _handle_authentication_stage(self, chat_id: int, telegram_user_id: int, session) -> None:
        """Handle user authentication by checking telegram_id in database"""
        logger.info(f"🔐 Authentication check for chat {chat_id}, telegram_user_id: {telegram_user_id}")
        
        try:
            # Check if telegram_id exists in database
            user = self.db_service.get_user_by_telegram_id(telegram_user_id)
            
            if user:
                # User is registered, proceed to main flow
                logger.info(f"✅ User authenticated successfully for telegram_id: {telegram_user_id}")
                # Store telegram_user_id in session for future use
                session.data.telegram_user_id = telegram_user_id
                session.stage = "await_initial_choice"
                self.telegram.send_welcome_message(chat_id)
            else:
                # User not found, ask for phone number
                session.stage = "await_phone_verification"
                self.telegram.send_message(
                    chat_id,
                    "Hi! To start using CraftBuddy bot, please share your contact number."
                )
        except Exception as e:
            logger.error(f"💥 Error during authentication for chat {chat_id}: {e}")
            self.telegram.send_message(
                chat_id,
                "Sorry, there was an error during authentication. Please try again with /restart."
            )
    
    def _handle_phone_verification_stage(self, chat_id: int, phone_number: str, telegram_user_id: int, session) -> None:
        """Handle phone number verification and telegram_id update"""
        
        try:
            # Clean phone number (remove spaces, dashes, etc.)
            cleaned_phone = phone_number.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            
            # Check if phone number exists in database
            user = self.db_service.get_user_by_phone_number(cleaned_phone)
            
            if user:
                # Phone number found, update telegram_id
                updated_user = self.db_service.update_user_telegram_id(cleaned_phone, telegram_user_id)
                
                if updated_user:
                    # Store telegram_user_id in session for future use
                    session.data.telegram_user_id = telegram_user_id
                    session.stage = "await_initial_choice"
                    self.telegram.send_welcome_message(chat_id)
                else:
                    logger.error(f"❌ Failed to update telegram_id for phone: {cleaned_phone}")
                    self.telegram.send_message(
                        chat_id,
                        "Sorry, there was an error updating your information. Please try again with /restart."
                    )
            else:
                # Phone number not found in database
                self.telegram.send_message(
                    chat_id,
                    "Oops, it looks like you haven't registered yourself on the site. Please sign in on: https://craftbuddy.com"
                )
                # Reset session so they can try again
                session.reset()
                
        except Exception as e:
            logger.error(f"💥 Error during phone verification for chat {chat_id}: {e}")
            self.telegram.send_message(
                chat_id,
                "Sorry, there was an error verifying your phone number. Please try again with /restart."
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
                
                # Get AI name suggestions
                cloud_image_url = session.data.cloud_image_url
                if cloud_image_url:
                    
                    try:
                        # Add timeout handling for AI call
                        import time
                        start_time = time.time()
                        name_suggestions = self.gemini.get_product_name_suggestions(cloud_image_url)
                        end_time = time.time()
                        duration = end_time - start_time
                        
                        session.data.name_suggestions = name_suggestions
                        
                        # Move to name suggestions stage
                        session.stage = "upload_product_llm_name_suggestions"
                        self._show_name_suggestions(chat_id, name_suggestions)
                        
                    except Exception as e:
                        logger.error(f"AI name suggestions failed: {e}")
                        # Fallback to manual name entry if AI fails
                        session.stage = "upload_product_llm_name"
                        self.telegram.send_skip_keyboard(
                            chat_id,
                            "Now, please provide the *product name*. If you don't have an idea, you can skip this step.",
                            "skip_name"
                        )
                else:
                    logger.warning(f"No cloud image URL found, skipping AI suggestions")
                    # Fallback to manual name entry
                    session.stage = "upload_product_llm_name"
                    self.telegram.send_skip_keyboard(
                        chat_id,
                        "Now, please provide the *product name*. If you don't have an idea, you can skip this step.",
                        "skip_name"
                    )
            else:
                logger.error(f"Image upload failed: {error_msg}")
                self.telegram.send_message(chat_id, error_msg or "There was an issue with your image. Please try again.")
        else:
            logger.warning(f"No file ID found in message")
            self.telegram.send_message(chat_id, "Please upload a product image to get started.")
    
    def _handle_name_stage(self, chat_id: int, text: str, session) -> None:
        """Handle product name input stage"""
        if text:
            session.data.product_name = text
            session.stage = "upload_product_llm_price"
            self.telegram.send_skip_keyboard(
                chat_id,
                "Thank you! Now please provide the *product price*. Make sure to enter amount in integer (For ex: 9000 not 9k). If you're unsure, you can skip this step.",
                "skip_price"
            )
    
    def _handle_price_stage(self, chat_id: int, text: str, session) -> None:
        """Handle product price input stage"""
        if text:
            session.data.price = text
            # Start AI specification suggestions flow
            self._start_spec_suggestions_flow(chat_id, session)
    
    def _handle_specs_stage(self, chat_id: int, text: str, session) -> None:
        """Handle specifications input stage"""
        logger.info(f"🔄 _handle_specs_stage called for chat {chat_id} with text: '{text}'")
        
        if not text:
            logger.warning(f"⚠️  Empty text received in specs stage for chat {chat_id}")
            return
        
        # Process the specification answer
        logger.info(f"📋 Processing specification answer...")
        has_more = self.product.process_specification_answer(chat_id, session, text)
        
        logger.info(f"🔄 has_more: {has_more}")
        
        if not has_more:
            # All specifications collected, finalize product
            logger.info(f"🎯 All specifications collected, calling _finalize_product_upload...")
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
        logger.info(f"🎯 _finalize_product_upload called for chat {chat_id}")
        logger.info(f"📊 Current session stage: {session.stage}")
        logger.info(f"🌐 Session cloud_image_url: {session.data.cloud_image_url}")
        logger.info(f"📝 Session product_name: {session.data.product_name}")
        logger.info(f"💰 Session price: {session.data.price}")
        logger.info(f"📋 Session specifications: {session.data.specifications}")
        
        # Get telegram_user_id from session data
        telegram_user_id = session.data.telegram_user_id
        if not telegram_user_id:
            logger.error(f"❌ No telegram_user_id found in session for chat {chat_id}")
            self.telegram.send_message(chat_id, "Error: Authentication issue. Please restart with /restart.")
            session.reset()
            return
        
        product = self.product.finalize_product(chat_id, telegram_user_id, session)
        
        if product:
            logger.info(f"✅ Product finalization successful, updating session stage to 'done'")
            session.stage = "done"
            session.llm_history = []
            self.product.send_product_summary(chat_id, product)
        else:
            logger.error(f"❌ Product finalization failed for chat {chat_id}")
            self.telegram.send_message(chat_id, "Error: Failed to process product. Please start again.")
            session.reset()
            self.telegram.send_welcome_message(chat_id)
    
    def _send_status(self, chat_id: int, session) -> None:
        """Send session status information"""
        try:
            llm_hist_display = json.dumps(session.llm_history, indent=2, ensure_ascii=False)
            llm_hist_display = (llm_hist_display[:1000] + '...') if len(llm_hist_display) > 1000 else llm_hist_display
            
            data_dict = {
                "telegram_user_id": session.data.telegram_user_id,
                "product_name": session.data.product_name,
                "price": session.data.price,
                "specifications": session.data.specifications,
                "cloud_image_url": session.data.cloud_image_url,
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
    
    def _show_name_suggestions(self, chat_id: int, name_suggestions: List[str]) -> None:
        """Show AI name suggestions as inline keyboard"""
        
        # Create inline keyboard with name suggestions
        keyboard_buttons = []
        for i, name in enumerate(name_suggestions):
            keyboard_buttons.append([{"text": name, "callback_data": f"select_name_{i}"}])
        
        # Add option for custom name
        keyboard_buttons.append([{"text": "✏️ Enter Custom Name", "callback_data": "custom_name"}])
        
        keyboard = {"inline_keyboard": keyboard_buttons}
        
        self.telegram.send_message(
            chat_id,
            "🤖 *AI Product Name Suggestions*\n\nChoose one of these AI-generated names or enter your own:",
            reply_markup=json.dumps(keyboard)
        )
    
    def _handle_name_suggestions_stage(self, chat_id: int, text: str, session) -> None:
        """Handle text input during name suggestions stage (for custom name)"""
        if text and text.strip():
            session.data.product_name = text.strip()
            self._proceed_to_price_stage(chat_id, session)
        else:
            self.telegram.send_message(chat_id, "Please enter a product name or use the suggestions above.")
    
    def _show_spec_suggestions(self, chat_id: int, spec_key: str, question: str, suggestions: List[str], session) -> None:
        """Show AI specification suggestions as inline keyboard"""
        
        # Create inline keyboard with spec suggestions
        keyboard_buttons = []
        for i, suggestion in enumerate(suggestions):
            keyboard_buttons.append([{"text": suggestion, "callback_data": f"select_spec_{spec_key}_{i}"}])
        
        # Add option for custom answer
        keyboard_buttons.append([{"text": "✏️ Enter Custom Answer", "callback_data": f"custom_spec_{spec_key}"}])
        keyboard_buttons.append([{"text": "⏭️ Skip This", "callback_data": f"skip_spec_{spec_key}"}])
        
        keyboard = {"inline_keyboard": keyboard_buttons}
        
        current_index = session.data.current_spec_index + 1
        total_questions = len(session.data.spec_suggestions)
        
        self.telegram.send_message(
            chat_id,
            f"🤖 *Question {current_index}/{total_questions}*\n\n*{question}*\n\nChoose an AI suggestion or enter your own:",
            reply_markup=json.dumps(keyboard)
        )
    
    def _handle_specs_suggestions_stage(self, chat_id: int, text: str, session) -> None:
        """Handle text input during spec suggestions stage (for custom answers)"""
        current_spec_key = session.data.current_spec_key
        
        if text and text.strip() and current_spec_key:
            # Store the custom answer
            session.data.specifications[current_spec_key] = text.strip()
            self._move_to_next_spec_suggestion(chat_id, session)
        else:
            self.telegram.send_message(chat_id, "Please enter your answer or use the suggestions above.")
    
    def _proceed_to_price_stage(self, chat_id: int, session) -> None:
        """Proceed to price input stage after name selection"""
        session.stage = "upload_product_llm_price"
        self.telegram.send_skip_keyboard(
            chat_id,
            f"Perfect! Product name: *{session.data.product_name}*\n\nNow please provide the *product price*:",
            "skip_price"
        )
    
    def _start_spec_suggestions_flow(self, chat_id: int, session) -> None:
        """Start the specification suggestions flow"""
        
        if not session.data.product_name or not session.data.cloud_image_url:
            # Fallback to regular specs flow
            session.stage = "upload_product_llm_specs"
            self.product.start_specification_questions(chat_id, session, "")
            return
        
        # Get AI specification suggestions
        spec_suggestions = self.gemini.get_specification_suggestions(
            session.data.cloud_image_url, 
            session.data.product_name
        )
        
        session.data.spec_suggestions = spec_suggestions
        session.data.current_spec_index = 0
        session.stage = "upload_product_llm_specs_suggestions"
        
        # Show first specification question with suggestions
        if spec_suggestions:
            first_spec_key = list(spec_suggestions.keys())[0]
            first_spec_data = spec_suggestions[first_spec_key]
            session.data.current_spec_key = first_spec_key
            
            self._show_spec_suggestions(
                chat_id, 
                first_spec_key, 
                first_spec_data["question"], 
                first_spec_data["suggestions"],
                session
            )
        else:
            # Fallback to regular specs flow
            session.stage = "upload_product_llm_specs"
            self.product.start_specification_questions(chat_id, session, "")
    
    def _move_to_next_spec_suggestion(self, chat_id: int, session) -> None:
        """Move to next specification suggestion or finish"""
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
            telegram_user_id = session.data.telegram_user_id
            if telegram_user_id:
                self._finalize_product_upload(chat_id, session)
            else:
                logger.error(f"No telegram_user_id found for chat {chat_id}")
                self.telegram.send_message(chat_id, "Authentication error. Please restart with /restart.")
