"""Gemini AI service for CraftBuddy bot"""
import json
import traceback
import httpx
import io
from typing import Dict, Optional, Any, List

from src.config.settings import config
from src.constants.artisan_specs import ARTISAN_SPECIFICATIONS, DEFAULT_FALLBACK_SPECS
from src.utils.logger import get_logger

logger = get_logger(__name__)

class GeminiService:
    """Service for Gemini AI interactions"""
    
    def __init__(self):
        self.enabled = config.USE_GEMINI
        self.model = None
        
        if self.enabled:
            try:
                import google.generativeai as genai
                genai.configure(api_key=config.GEMINI_API_KEY)
                self.model = genai.GenerativeModel(config.GEMINI_MODEL)
                logger.info("Gemini AI service initialized successfully")
            except ImportError:
                logger.debug("Google Generative AI library not installed - AI features disabled")
                self.enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.enabled = False
        else:
            logger.info("Gemini AI service disabled - no API key provided")
    
    def analyze_product_name_for_specs(self, product_name: str) -> Dict[str, str]:
        """
        Analyze product name and determine relevant specifications
        
        Args:
            product_name: Name of the product
            
        Returns:
            Dictionary of specification questions
        """
        if not self.enabled:
            return {
                f"{key}": f"{question}".format(product_name=product_name)
                for key, question in DEFAULT_FALLBACK_SPECS.items()
            }
        
        try:
            available_specs = list(ARTISAN_SPECIFICATIONS.keys())
            spec_descriptions = [
                f"{key}: {desc}" 
                for key, desc in list(ARTISAN_SPECIFICATIONS.items())[:25]
            ]
            
            prompt = (
                f"Analyze this product name: '{product_name}' and determine the TOP 5 MOST IMPORTANT specifications for an artisan marketplace. "
                f"Select EXACTLY 5 specifications from this comprehensive list:\\n\\n"
                f"{chr(10).join(spec_descriptions)}\\n\\n"
                f"Additional specifications available: {', '.join(available_specs[25:])}\\n\\n"
                f"Rules:\\n"
                f"1. Choose ONLY the 5 most essential specs for '{product_name}'\\n"
                f"2. Prioritize: material, colour, craft_style for most products\\n"
                f"3. For textiles: prioritize material, colour, craft_style, pattern, length\\n"
                f"4. For clothing: prioritize material, colour, silhouette, occasion, care_instructions\\n"
                f"5. For pottery/ceramics: prioritize material, shape, finish, usage, craft_style\\n"
                f"6. For jewelry: prioritize material, colour, embellishment, occasion, weight\\n"
                f"7. For home decor: prioritize material, usage, colour, dimensions, craft_style\\n"
                f"8. Skip irrelevant specs completely\\n\\n"
                f"Return a JSON object with EXACTLY 5 specification keys and custom questions as values.\\n"
                f"Make questions specific to '{product_name}' and artisan-friendly.\\n"
                f"Example: {{'material': 'What fabric is this {product_name} made from?', 'colour': 'What is the primary color of your {product_name}?'}}"
            )
            
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean JSON response
            response_text = self._clean_json_response(response_text)
            questions = json.loads(response_text)
            
            # Validate and filter questions
            valid_questions = {}
            for spec_key, question in questions.items():
                if spec_key in ARTISAN_SPECIFICATIONS:
                    valid_questions[spec_key] = question
            
            # Ensure exactly 5 questions
            if len(valid_questions) > 5:
                valid_questions = dict(list(valid_questions.items())[:5])
            
            if len(valid_questions) == 5:
                return valid_questions
            else:
                logger.warning(f"Generated {len(valid_questions)} questions instead of 5, falling back to default")
                return self._get_fallback_specs(product_name)
                
        except Exception as e:
            logger.error(f"Error analyzing product name for specs: {e}")
            return self._get_fallback_specs(product_name)
    
    def get_product_name_suggestions(self, image_url: str) -> List[str]:
        """
        Get 3 product name suggestions based on image analysis
        
        Args:
            image_url: URL to product image (GCS URL)
            
        Returns:
            List of 3 product name suggestions
        """
        if not self.enabled:
            logger.warning(f"Gemini not enabled, returning fallback suggestions")
            return ["Handcrafted Product", "Artisan Creation", "Traditional Craft"]
        
        try:
            image = self._load_image_from_url(image_url)
            if not image:
                logger.warning(f"Failed to load image, returning fallback")
                return ["Handcrafted Product", "Artisan Creation", "Traditional Craft"]
            
            prompt = (
                "Analyze this artisan product image and suggest exactly 3 creative, marketable product names. "
                "Focus on traditional craftsmanship and cultural heritage. "
                "Each name should be 2-4 words, appealing to buyers, and highlight the artisan nature. "
                "Return only a JSON array of exactly 3 strings, nothing else. "
                "Example: [\"Handwoven Cotton Scarf\", \"Traditional Block Print Textile\", \"Artisan Dyed Fabric\"]"
            )
            
            response = self.model.generate_content([prompt, image])
            
            response_text = self._clean_json_response(response.text.strip())
            
            suggestions = json.loads(response_text)
            if isinstance(suggestions, list) and len(suggestions) == 3:
                logger.info(f"Successfully parsed {len(suggestions)} suggestions")
                return suggestions
            else:
                logger.warning(f"Invalid suggestions format: {suggestions}, using fallback")
                return ["Handcrafted Product", "Artisan Creation", "Traditional Craft"]
                
        except Exception as e:
            logger.error(f"Error getting product name suggestions: {e}")
            return ["Handcrafted Product", "Artisan Creation", "Traditional Craft"]
    
    def get_specification_suggestions(self, image_url: str, product_name: str) -> Dict[str, Dict[str, List[str]]]:
        """
        Get specification questions with 3 suggestions each based on image and product name
        
        Args:
            image_url: URL to product image (GCS URL)
            product_name: Chosen product name
            
        Returns:
            Dictionary with spec questions and their suggestions
        """
        if not self.enabled:
            return self._get_fallback_spec_suggestions(product_name)
        
        try:
            image = self._load_image_from_url(image_url)
            if not image:
                return self._get_fallback_spec_suggestions(product_name)
            
            # First get the relevant specification questions for this product
            spec_questions = self.analyze_product_name_for_specs(product_name)
            
            # Now get 3 suggestions for each specification based on the image
            prompt = (
                f"Analyze this image of '{product_name}' and provide exactly 3 specific suggestions for each specification. "
                f"Base suggestions on what you can see in the image and typical artisan product characteristics. "
                f"Specifications to suggest for: {list(spec_questions.keys())} "
                f"Return a JSON object where each specification key has an array of exactly 3 specific suggestions. "
                f"Make suggestions realistic and based on visual analysis. "
                f"Example format: {{"
                f"\"material\": [\"Cotton\", \"Silk\", \"Linen\"], "
                f"\"colour\": [\"Deep Blue\", \"Indigo\", \"Navy Blue\"]"
                f"}}"
            )
            
            response = self.model.generate_content([prompt, image])
            response_text = self._clean_json_response(response.text.strip())
            
            suggestions = json.loads(response_text)
            
            # Combine questions with suggestions
            result = {}
            for spec_key, question in spec_questions.items():
                if spec_key in suggestions and isinstance(suggestions[spec_key], list):
                    result[spec_key] = {
                        "question": question,
                        "suggestions": suggestions[spec_key][:3]  # Ensure only 3 suggestions
                    }
                else:
                    # Fallback suggestions for this spec
                    result[spec_key] = {
                        "question": question,
                        "suggestions": self._get_fallback_suggestions_for_spec(spec_key)
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting specification suggestions: {e}")
            return self._get_fallback_spec_suggestions(product_name)
    
    def analyze_product_image(
        self,
        image_url: str,
        product_name: Optional[str] = None,
        price: Optional[str] = None,
        specifications: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze product image and suggest improvements
        
        Args:
            image_url: URL to product image (GCS URL)
            product_name: Optional existing product name
            price: Optional existing price
            specifications: Optional existing specifications
            
        Returns:
            Dictionary with suggestions
        """
        if not self.enabled:
            return {
                "name": product_name or "Product Name",
                "price": price or "$0.00",
                "specifications": specifications or "Product specifications"
            }
        
        try:
            image = self._load_image_from_url(image_url)
            if not image:
                return {
                    "name": product_name or "Product Name",
                    "price": price or "$0.00",
                    "specifications": specifications or "Product specifications"
                }
            
            prompt_parts = [
                "You are an AI assistant helping sellers describe their products. "
                "Analyze this product image and provide suggestions in exactly 20 words or less for each field. "
                "Respond in JSON format with keys: 'name', 'price', 'specifications'. "
            ]
            
            if product_name:
                prompt_parts.append(f"The user provided name: '{product_name}'. ")
            else:
                prompt_parts.append("Suggest a product name. ")
                
            if price:
                prompt_parts.append(f"The user provided price: '{price}'. ")
            else:
                prompt_parts.append("Suggest a reasonable price. ")
                
            if specifications:
                prompt_parts.append(f"The user provided specs: '{specifications}'. ")
            else:
                prompt_parts.append("Suggest key specifications. ")
            
            prompt_parts.append("Keep each suggestion to 20 words maximum.")
            
            response = self.model.generate_content([" ".join(prompt_parts), image])
            response_text = self._clean_json_response(response.text.strip())
            
            suggestions = json.loads(response_text)
            return suggestions
            
        except Exception as e:
            logger.error(f"Gemini image analysis error: {e}")
            traceback.print_exc()
            return {
                "name": product_name or "Product Name",
                "price": price or "$0.00",
                "specifications": specifications or "Product specifications"
            }
    
    def generate_description_and_standardize_price(
        self,
        image_url: str,
        product_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate product description and standardize price format
        
        Args:
            image_url: URL to product image (GCS URL)
            product_data: Product data dictionary
            
        Returns:
            Dictionary with description and standardized_price
        """
        if not self.enabled:
            return self._fallback_description_and_price(product_data)
        
        try:
            image = self._load_image_from_url(image_url)
            if not image:
                return self._fallback_description_and_price(product_data)
            
            # Extract user-provided specifications
            user_specs = product_data.get('specifications', {})
            provided_details = []
            for key, value in user_specs.items():
                if value and value.strip():
                    provided_details.append(f"{key}: {value}")
            
            prompt = (
                f"Analyze this product image of '{product_data.get('product_name', 'product')}' and create a 40-50 word marketing description. "
                f"Use ONLY the following user-provided details and what you can see in the image:\\n"
                f"User provided: {', '.join(provided_details) if provided_details else 'No specific details provided'}\\n\\n"
                f"Rules:\\n"
                f"1. Base description primarily on what you can see in the image\\n"
                f"2. Include user-provided specifications if given\\n"
                f"3. Do NOT make up dimensions, colors, or materials not visible or provided\\n"
                f"4. Keep it concise and marketing-friendly\\n"
                f"5. Focus on artisan craftsmanship and visible features\\n\\n"
                f"Also convert the price '{product_data.get('price', '')}' to an integer (extract numeric value only).\\n"
                f"Return JSON with keys 'description' and 'standardized_price'.\\n"
                f"Price should be just the integer value (e.g., 250 for 'Rs. 250')."
            )
            
            response = self.model.generate_content([prompt, image])
            response_text = self._clean_json_response(response.text.strip())
            
            result = json.loads(response_text)
            return result
            
        except Exception as e:
            logger.error(f"Error generating description and price: {e}")
            return self._fallback_description_and_price(product_data)
    
    def chat_response(
        self,
        user_input: str,
        history: List[Any],
        has_local_image: bool = False
    ) -> tuple[str, List[Any]]:
        """
        Generate chat response using Gemini
        
        Args:
            user_input: User's input text
            history: Chat history
            has_local_image: Whether user sent an image
            
        Returns:
            Tuple of (response_text, updated_history)
        """
        if not self.enabled:
            return "I'm having trouble understanding right now. Please try again.", history
        
        try:
            sys_prompt = (
                "You are a helpful and polite AI assistant for a seller bot. "
                "Your task is to respond to the user's input with a single, professional sentence. "
                "Do not use conversational fillers. "
                "Acknowledge the user's input and then politely ask for the next piece of information. "
                "Here are some example prompts: 'Please provide the product name.', 'Please provide the product price.', 'Please provide the product specifications.'. "
                "When the user provides the final piece of information, do not ask for anything else. Simply provide a concluding statement."
            )
            
            parts = [sys_prompt]
            
            if user_input:
                parts.append(f"The user's last input was: '{user_input}'. Please respond appropriately.")
            elif has_local_image:
                parts.append("The user has sent an image. Please acknowledge this and ask for the product name.")
            
            chat = self.model.start_chat(history=history)
            response = chat.send_message(parts)
            
            return response.text.strip(), chat.history
            
        except Exception as e:
            logger.error(f"Gemini LLM error: {e}")
            traceback.print_exc()
            return "I'm having trouble understanding right now. Please try again.", history
    
    def _clean_json_response(self, response_text: str) -> str:
        """Clean JSON response from code blocks"""
        if response_text.startswith("```json"):
            return response_text[7:-3].strip()
        elif response_text.startswith("```"):
            return response_text[3:-3].strip()
        return response_text
    
    def _get_fallback_specs(self, product_name: str) -> Dict[str, str]:
        """Get fallback specification questions"""
        return {
            "material": f"What is the primary material of your {product_name}?",
            "colour": f"What is the main color of your {product_name}?",
            "craft_style": f"What traditional craft technique was used for this {product_name}?",
            "occasion": f"What occasions is this {product_name} suitable for?",
            "care_instructions": f"How should this {product_name} be maintained?"
        }
    
    def _load_image_from_url(self, image_url: str):
        """Load PIL Image from URL"""
        try:
            from PIL import Image
            
            with httpx.Client() as client:
                response = client.get(image_url)
                response.raise_for_status()
                image_data = response.content
                
            image = Image.open(io.BytesIO(image_data))
            logger.info(f"Successfully loaded image from URL: {image_url}")
            return image
            
        except Exception as e:
            logger.error(f"Failed to load image from URL {image_url}: {e}")
            return None
    
    def _fallback_description_and_price(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback description and price extraction"""
        import re
        
        price_str = product_data.get('price', '0')
        price_match = re.search(r'\d+', str(price_str))
        standardized_price = int(price_match.group()) if price_match else 0
        
        return {
            "description": "Premium quality product with excellent craftsmanship and attention to detail.",
            "standardized_price": standardized_price
        }
    
    def _get_fallback_spec_suggestions(self, product_name: str) -> Dict[str, Dict[str, List[str]]]:
        """Get fallback specification suggestions when AI is not available"""
        fallback_specs = self._get_fallback_specs(product_name)
        
        result = {}
        for spec_key, question in fallback_specs.items():
            result[spec_key] = {
                "question": question,
                "suggestions": self._get_fallback_suggestions_for_spec(spec_key)
            }
        return result
    
    def _get_fallback_suggestions_for_spec(self, spec_key: str) -> List[str]:
        """Get fallback suggestions for a specific specification"""
        fallback_suggestions = {
            "material": ["Cotton", "Silk", "Wool"],
            "colour": ["Natural", "Blue", "Red"],
            "craft_style": ["Handwoven", "Block Print", "Embroidered"],
            "occasion": ["Daily Wear", "Festive", "Casual"],
            "care_instructions": ["Hand Wash", "Dry Clean", "Machine Wash"],
            "pattern": ["Plain", "Floral", "Geometric"],
            "shape": ["Round", "Square", "Rectangular"],
            "usage": ["Decorative", "Functional", "Ceremonial"],
            "finish": ["Smooth", "Textured", "Glossy"],
            "season": ["All Season", "Summer", "Winter"]
        }
        
        return fallback_suggestions.get(spec_key, ["Option 1", "Option 2", "Option 3"])
