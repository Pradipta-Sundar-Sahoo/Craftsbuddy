"""Product data models"""
from typing import Dict, Optional
from dataclasses import dataclass, field

@dataclass
class Product:
    """Product data model"""
    product_name: str = "Product Name"
    price: int = 0
    description: str = "Product description"
    specifications: Dict[str, str] = field(default_factory=dict)
    cloud_image_url: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "product_name": self.product_name,
            "price": self.price,
            "description": self.description,
            "specifications": self.specifications,
            "cloud_image_url": self.cloud_image_url
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Product':
        """Create Product from dictionary"""
        return cls(
            product_name=data.get("product_name", "Product Name"),
            price=data.get("price", 0),
            description=data.get("description", "Product description"),
            specifications=data.get("specifications", {}),
            cloud_image_url=data.get("cloud_image_url")
        )
    
    def is_valid(self) -> bool:
        """Check if product has minimum required data"""
        return bool(self.product_name and self.product_name != "Product Name")
    

@dataclass
class SpecificationQuestions:
    """Specification questions for a product"""
    questions: Dict[str, str] = field(default_factory=dict)
    current_index: int = 0
    
    @property
    def total_questions(self) -> int:
        return len(self.questions)
    
    @property
    def question_keys(self) -> list:
        return list(self.questions.keys())
    
    def get_current_question(self) -> Optional[tuple]:
        """Get current question key and text"""
        if self.current_index < len(self.question_keys):
            key = self.question_keys[self.current_index]
            return key, self.questions[key]
        return None
    
    def move_to_next(self) -> None:
        """Move to next question"""
        self.current_index += 1
    
    def is_complete(self) -> bool:
        """Check if all questions have been asked"""
        return self.current_index >= len(self.questions)
