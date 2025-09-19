"""Product service for handling product-related operations"""
from typing import Dict, Optional, Tuple

from src.models.product import Product, SpecificationQuestions
from src.models.session import Session
from src.services.gemini_service import GeminiService
from src.services.telegram_service import TelegramService
from src.services.gcs_service import GCSService
from src.services.database_service import DatabaseService
from src.utils.file_utils import get_file_extension_from_path
from src.utils.logger import get_logger
from src.config.settings import config

logger = get_logger(__name__)

class ProductService:
    """Service for product-related operations"""
    
    def __init__(self, telegram_service: TelegramService, gemini_service: GeminiService):
        logger.info("🔄 Initializing ProductService...")
        self.telegram = telegram_service
        self.gemini = gemini_service
        
        # Initialize Database Service
        try:
            self.db_service = DatabaseService()
            logger.info("✅ DatabaseService initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize DatabaseService: {e}")
            raise
        
        # Initialize Google Cloud Storage service (required)
        if not config.USE_GCS or not config.GCS_BUCKET_NAME:
            logger.error(f"❌ GCS configuration missing - USE_GCS: {config.USE_GCS}, BUCKET: {config.GCS_BUCKET_NAME}")
            raise ValueError("GCS configuration is required - set GCS_BUCKET_NAME and optionally GCS_CREDENTIALS_PATH")
        
        try:
            self.gcs_service = GCSService(
                bucket_name=config.GCS_BUCKET_NAME,
                credentials_path=config.GCS_CREDENTIALS_PATH
            )
            logger.info("✅ GCS service initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize GCS service: {e}")
            raise ValueError("Failed to initialize GCS service - check your configuration")
        
        logger.info("✅ ProductService fully initialized")
    
    def handle_image_upload(
        self,
        file_id: str,
        chat_id: int,
        session: Session
    ) -> Tuple[bool, Optional[str]]:
        """
        Handle product image upload to Google Cloud Storage
        
        Args:
            file_id: Telegram file ID
            chat_id: Chat ID
            session: User session
            
        Returns:
            Tuple of (success, error_message)
        """
        logger.info(f"🔄 Starting image upload process for chat {chat_id}, file_id: {file_id}")
        
        try:
            # Get file info from Telegram
            logger.info(f"🔄 Getting file info from Telegram for file_id: {file_id}")
            file_path = self.telegram.get_file_info(file_id)
            if not file_path:
                logger.error(f"❌ Failed to get file info from Telegram for file_id: {file_id}")
                return False, "Failed to get file information from Telegram"
            
            logger.info(f"✅ Got file path from Telegram: {file_path}")
            
            # Download file content
            logger.info(f"🔄 Downloading file content from Telegram...")
            file_content = self.telegram.download_file(file_path)
            if not file_content:
                logger.error(f"❌ Failed to download file content from Telegram")
                return False, "Failed to download image from Telegram"
            
            logger.info(f"✅ Downloaded file content: {len(file_content)} bytes")
            
            file_extension = get_file_extension_from_path(file_path)
            logger.info(f"📄 File extension detected: {file_extension}")
            
            # Upload to Google Cloud Storage
            logger.info(f"🔄 Uploading to GCS...")
            success, cloud_url, error_msg = self.gcs_service.upload_image(
                file_content, chat_id, file_extension
            )
            
            if success and cloud_url:
                # Store cloud URL in session
                session.data.cloud_image_url = cloud_url
                logger.info(f"✅ Image uploaded to GCS successfully!")
                logger.info(f"🌐 Cloud URL: {cloud_url}")
                logger.info(f"💾 Stored in session for chat {chat_id}")
                return True, None
            else:
                logger.error(f"❌ GCS upload failed: {error_msg}")
                return False, error_msg or "Failed to upload image to cloud storage"
            
        except Exception as e:
            logger.error(f"💥 Exception in image upload for chat {chat_id}: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
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
        Finalize product with AI processing and save to database
        
        Args:
            chat_id: Chat ID
            session: User session
            
        Returns:
            Finalized Product object or None if failed
        """
        logger.info(f"🔄 Starting product finalization for chat {chat_id}")
        
        try:
            self.telegram.send_message(
                chat_id,
                "Processing your product information with AI assistance..."
            )
            
            # Get cloud image URL from session
            cloud_image_url = session.data.cloud_image_url
            logger.info(f"🌐 Cloud image URL from session: {cloud_image_url}")
            
            if not cloud_image_url:
                logger.error(f"❌ No cloud image URL found in session for chat {chat_id}")
                logger.error(f"📊 Session data: {vars(session.data)}")
                return None
            
            # Create product data dictionary for AI processing
            product_data = {
                "product_name": session.data.product_name or "Product Name",
                "price": session.data.price or "0",
                "specifications": session.data.specifications
            }
            logger.info(f"📋 Product data for AI: {product_data}")
            
            # Generate description and standardize price using AI with cloud URL
            logger.info(f"🔄 Calling Gemini AI for description and price...")
            desc_and_price = self.gemini.generate_description_and_standardize_price(
                cloud_image_url,
                product_data
            )
            logger.info(f"🤖 AI response: {desc_and_price}")
            
            # Get or create seller
            logger.info(f"🔄 Getting/creating seller for chat {chat_id}")
            seller = self.db_service.get_seller_by_chat_id(chat_id)
            if not seller:
                logger.info(f"👤 Creating new seller for chat {chat_id}")
                seller = self.db_service.create_seller(
                    chat_id=chat_id,
                    name=f"User_{chat_id}"
                )
                if not seller:
                    logger.error(f"❌ Failed to create seller for chat {chat_id}")
                    return None
                logger.info(f"✅ Created seller with ID: {seller.id}")
            else:
                logger.info(f"✅ Found existing seller with ID: {seller.id}")
            
            # Save product to database
            logger.info(f"💾 Saving product to database...")
            db_product = self.db_service.create_product(
                seller_id=seller.id,
                product_name=product_data["product_name"],
                price=desc_and_price.get("standardized_price", 0),
                description=desc_and_price.get("description", "Product description"),
                cloud_image_url=cloud_image_url,
                specifications=session.data.specifications
            )
            
            if not db_product:
                logger.error(f"❌ Failed to save product to database for chat {chat_id}")
                return None
            
            logger.info(f"✅ Product saved to database successfully!")
            logger.info(f"🆔 Product ID: {db_product.id}")
            logger.info(f"📝 Product name: {db_product.product_name}")
            logger.info(f"💰 Price: {db_product.price}")
            logger.info(f"🌐 Cloud URL: {db_product.cloud_image_url}")
            
            # Create Product dataclass for return (for consistency with existing code)
            product = Product(
                product_name=db_product.product_name,
                price=db_product.price,
                description=db_product.description,
                specifications=session.data.specifications,
                cloud_image_url=db_product.cloud_image_url
            )
            
            logger.info(f"🎉 Product finalization completed successfully for chat {chat_id}")
            return product
            
        except Exception as e:
            logger.error(f"💥 Exception in product finalization for chat {chat_id}: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
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
