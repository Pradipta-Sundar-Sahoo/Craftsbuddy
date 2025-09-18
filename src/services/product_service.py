"""Product service for handling product-related operations"""
from typing import Dict, Optional, Tuple
import os

from src.models.product import Product, SpecificationQuestions
from src.models.session import Session
from src.services.gemini_service import GeminiService
from src.services.telegram_service import TelegramService
from src.utils.file_utils import save_image_file, get_file_extension_from_path
from src.utils.logger import get_logger
from src.config.settings import config

logger = get_logger(__name__)

class ProductService:
    """Service for product-related operations"""
    
    def __init__(self, telegram_service: TelegramService, gemini_service: GeminiService):
        self.telegram = telegram_service
        self.gemini = gemini_service
        
        # Ensure directories exist
        os.makedirs(config.IMAGE_SAVE_DIR, exist_ok=True)
        os.makedirs(config.PRODUCT_DATA_DIR, exist_ok=True)
    
    def handle_image_upload(
        self,
        file_id: str,
        chat_id: int,
        session: Session
    ) -> Tuple[bool, Optional[str]]:
        """
        Handle product image upload
        
        Args:
            file_id: Telegram file ID
            chat_id: Chat ID
            session: User session
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get file info from Telegram
            file_path = self.telegram.get_file_info(file_id)
            if not file_path:
                return False, "Failed to get file information from Telegram"
            
            # Download file content
            file_content = self.telegram.download_file(file_path)
            if not file_content:
                return False, "Failed to download image from Telegram"
            
            # Save image locally
            file_extension = get_file_extension_from_path(file_path)
            local_image_path = save_image_file(
                file_content,
                chat_id,
                file_extension,
                config.IMAGE_SAVE_DIR
            )
            
            # Store image path in session
            session.data.local_image_path = local_image_path
            logger.info(f"Image saved for chat {chat_id}: {local_image_path}")
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error handling image upload for chat {chat_id}: {e}")
            return False, "There was an error processing your image. Please try again."
    
    def start_specification_questions(
        self,
        chat_id: int,
        session: Session,
        context_message: str = ""
    ) -> None:
        """
        Start asking specification questions
        
        Args:
            chat_id: Chat ID
            session: User session
            context_message: Optional context message to prepend
        """
        product_name = session.data.product_name or "product"
        
        # Generate questions based on product name
        questions = self.gemini.analyze_product_name_for_specs(product_name)
        
        # Store questions in session
        session.data.spec_questions = questions
        session.data.current_spec_index = 0
        
        if questions:
            # Ask first question
            first_key = list(questions.keys())[0]
            first_question = questions[first_key]
            message = f"{context_message}Now I'll ask for the top 5 most important details about your *{product_name}*:\n\n**Question 1/5:** *{first_question}*"
            self.telegram.send_skip_keyboard(chat_id, message, f"skip_spec_{first_key}")
        else:
            # Fallback if no questions generated
            message = f"{context_message}Please provide specifications for your *{product_name}* (features, materials, dimensions, etc.). You can skip if you don't know."
            self.telegram.send_skip_keyboard(chat_id, message, "skip_specs")
    
    def process_specification_answer(
        self,
        chat_id: int,
        session: Session,
        answer: str
    ) -> bool:
        """
        Process specification answer and move to next question
        
        Args:
            chat_id: Chat ID
            session: User session
            answer: User's answer
            
        Returns:
            True if more questions remain, False if done
        """
        questions = session.data.spec_questions
        current_index = session.data.current_spec_index
        
        if not questions:
            # Fallback to storing general specifications
            session.data.specifications = {"general": answer}
            return False
        
        question_keys = list(questions.keys())
        
        if current_index < len(question_keys):
            # Store current answer
            current_key = question_keys[current_index]
            session.data.specifications[current_key] = answer
            
            # Move to next question
            session.data.current_spec_index = current_index + 1
            next_index = current_index + 1
            
            if next_index < len(question_keys):
                # Ask next question
                next_key = question_keys[next_index]
                next_question = questions[next_key]
                self.telegram.send_skip_keyboard(
                    chat_id,
                    f"**Question {next_index + 1}/5:** *{next_question}*",
                    f"skip_spec_{next_key}"
                )
                return True
            else:
                # All questions answered
                return False
        
        return False
    
    def skip_specification_question(
        self,
        chat_id: int,
        session: Session,
        skipped_spec_key: str
    ) -> bool:
        """
        Skip current specification question and move to next
        
        Args:
            chat_id: Chat ID
            session: User session
            skipped_spec_key: Key of skipped specification
            
        Returns:
            True if more questions remain, False if done
        """
        questions = session.data.spec_questions
        current_index = session.data.current_spec_index
        
        if not questions:
            return False
        
        question_keys = list(questions.keys())
        
        # Move to next question
        session.data.current_spec_index = current_index + 1
        next_index = current_index + 1
        
        if next_index < len(question_keys):
            # Ask next question
            next_key = question_keys[next_index]
            next_question = questions[next_key]
            self.telegram.send_skip_keyboard(
                chat_id,
                f"**Question {next_index + 1}/5:** *{next_question}*",
                f"skip_spec_{next_key}"
            )
            return True
        else:
            # All questions processed
            return False
    
    def finalize_product(
        self,
        chat_id: int,
        session: Session
    ) -> Optional[Product]:
        """
        Finalize product with AI processing and save
        
        Args:
            chat_id: Chat ID
            session: User session
            
        Returns:
            Finalized Product object or None if failed
        """
        try:
            self.telegram.send_message(
                chat_id,
                "Processing your product information with AI assistance..."
            )
            
            image_path = session.data.local_image_path
            if not image_path or not os.path.exists(image_path):
                logger.error(f"No valid image found for chat {chat_id}")
                return None
            
            # Create product data dictionary for AI processing
            product_data = {
                "product_name": session.data.product_name or "Product Name",
                "price": session.data.price or "0",
                "specifications": session.data.specifications
            }
            
            # Generate description and standardize price using AI
            desc_and_price = self.gemini.generate_description_and_standardize_price(
                image_path,
                product_data
            )
            
            # Create final Product object
            product = Product(
                product_name=product_data["product_name"],
                price=desc_and_price.get("standardized_price", 0),
                description=desc_and_price.get("description", "Product description"),
                specifications=session.data.specifications,
                local_image_path=image_path
            )
            
            # Save product to file
            filename = product.save_to_file(chat_id, config.PRODUCT_DATA_DIR)
            logger.info(f"Product saved for chat {chat_id}: {filename}")
            
            return product
            
        except Exception as e:
            logger.error(f"Error finalizing product for chat {chat_id}: {e}")
            return None
    
    def send_product_summary(self, chat_id: int, product: Product) -> None:
        """
        Send final product summary to user
        
        Args:
            chat_id: Chat ID
            product: Finalized product
        """
        final_msg = f"✅ *Product uploaded successfully!*\n\n"
        final_msg += f"*Name:* {product.product_name}\n"
        final_msg += f"*Price:* ₹{product.price}\n"
        final_msg += f"*Description:* {product.description}\n\n"
        final_msg += f"*Specifications:*\n"
        
        if product.specifications:
            for key, value in product.specifications.items():
                if value and value.strip():
                    formatted_key = key.replace('_', ' ').title()
                    final_msg += f"  • *{formatted_key}:* {value}\n"
        else:
            final_msg += "  • No specifications provided\n"
        
        self.telegram.send_message(chat_id, final_msg)
        self.telegram.send_welcome_message(chat_id)
    
    def extract_file_id_from_message(self, message: Dict) -> Optional[str]:
        """
        Extract file ID from message (photo or document)
        
        Args:
            message: Telegram message object
            
        Returns:
            File ID or None if not found
        """
        photos = message.get("photo")
        document = message.get("document")
        
        if photos:
            return self.telegram.extract_largest_photo(photos)
        elif document and document.get("mime_type", "").startswith("image/"):
            return document.get("file_id")
        
        return None
