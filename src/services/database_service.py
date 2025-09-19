"""Database service for CRUD operations"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.models.db_models import Seller, Product, ProductSpecification
from src.config.database import get_database_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

class DatabaseService:
    """Service for database operations"""
    
    def __init__(self):
        self.db_config = get_database_config()
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.db_config.get_session()
    
    # Seller operations
    def create_seller(self, name: str, brand_name: str = None, 
                     phone_number: str = None, address: str = None, telegram_id: int = None) -> Optional[Seller]:
        """Create a new seller"""
        logger.info(f"🔄 Creating seller - name: {name}, telegram_id: {telegram_id}")
        try:
            with self.get_session() as session:
                seller = Seller(
                    telegram_id=telegram_id,
                    name=name,
                    brand_name=brand_name,
                    phone_number=phone_number,
                    address=address
                )
                logger.info(f"📝 Seller object created, adding to session...")
                session.add(seller)
                logger.info(f"💾 Committing seller to database...")
                session.commit()
                session.refresh(seller)
                logger.info(f"✅ Seller created successfully with ID: {seller.id}")
                return seller
        except SQLAlchemyError as e:
            logger.error(f"❌ SQLAlchemy error creating seller: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return None
        except Exception as e:
            logger.error(f"💥 Unexpected error creating seller: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return None
    
# Removed get_seller_by_chat_id method - now using telegram_id for identification
    
    def get_seller_by_telegram_id(self, telegram_id: int) -> Optional[Seller]:
        """Get seller by telegram ID"""
        try:
            with self.get_session() as session:
                seller = session.query(Seller).filter(Seller.telegram_id == telegram_id).first()
                return seller
        except SQLAlchemyError as e:
            logger.error(f"Failed to get seller by telegram_id {telegram_id}: {e}")
            return None
    
    def get_seller_by_phone_number(self, phone_number: str) -> Optional[Seller]:
        """Get seller by phone number"""
        try:
            with self.get_session() as session:
                seller = session.query(Seller).filter(Seller.phone_number == phone_number).first()
                return seller
        except SQLAlchemyError as e:
            logger.error(f"Failed to get seller by phone_number {phone_number}: {e}")
            return None
    
    def update_seller_telegram_id(self, phone_number: str, telegram_id: int) -> Optional[Seller]:
        """Update seller's telegram_id by phone number"""
        try:
            with self.get_session() as session:
                seller = session.query(Seller).filter(Seller.phone_number == phone_number).first()
                if seller:
                    old_telegram_id = seller.telegram_id
                    seller.telegram_id = telegram_id
                    session.commit()
                    session.refresh(seller)
                    logger.info(f"Updated telegram_id for seller with phone: {phone_number}")
                return seller
        except SQLAlchemyError as e:
            logger.error(f"Failed to update seller telegram_id: {e}")
            return None
    
    def update_seller(self, telegram_id: int, **kwargs) -> Optional[Seller]:
        """Update seller information"""
        try:
            with self.get_session() as session:
                seller = session.query(Seller).filter(Seller.telegram_id == telegram_id).first()
                if seller:
                    for key, value in kwargs.items():
                        if hasattr(seller, key) and value is not None:
                            setattr(seller, key, value)
                    session.commit()
                    session.refresh(seller)
                    logger.info(f"Updated seller for telegram_id: {telegram_id}")
                return seller
        except SQLAlchemyError as e:
            logger.error(f"Failed to update seller: {e}")
            return None
    
    # Product operations
    def create_product(self, seller_id: int, product_name: str, price: int, 
                      description: str = None, local_image_path: str = None,
                      cloud_image_url: str = None,
                      specifications: Dict[str, str] = None) -> Optional[Product]:
        """Create a new product with specifications"""
        logger.info(f"🔄 Creating product: {product_name} for seller_id: {seller_id}")
        logger.info(f"💰 Price: {price}")
        logger.info(f"📝 Description: {description}")
        logger.info(f"🌐 Cloud URL: {cloud_image_url}")
        logger.info(f"📋 Specifications: {specifications}")
        
        try:
            with self.get_session() as session:
                logger.info(f"📝 Creating Product database object...")
                product = Product(
                    seller_id=seller_id,
                    product_name=product_name,
                    price=price,
                    description=description,
                    local_image_path=local_image_path,
                    cloud_image_url=cloud_image_url
                )
                
                logger.info(f"➕ Adding product to session...")
                session.add(product)
                logger.info(f"🔄 Flushing to get product ID...")
                session.flush()  # Get product ID
                logger.info(f"🆔 Product ID assigned: {product.id}")
                
                # Add specifications (INSIDE the session context)
                if specifications:
                    logger.info(f"📋 Adding {len(specifications)} specifications...")
                    for key, value in specifications.items():
                        logger.info(f"  • {key}: {value}")
                        spec = ProductSpecification(
                            product_id=product.id,
                            spec_key=key,
                            spec_value=value
                        )
                        session.add(spec)
                    logger.info(f"✅ All specifications added to session, committing...")
                else:
                    logger.info(f"📋 No specifications to add")
                
                # Commit regardless of whether there are specifications or not
                logger.info(f"💾 Committing product to database...")
                session.commit()
                session.refresh(product)
                logger.info(f"✅ Product created successfully!")
                return product
                
        except SQLAlchemyError as e:
            logger.error(f"❌ SQLAlchemy error creating product: {e}")
            import traceback
            traceback_str = traceback.format_exc()
            logger.error(f"📋 Traceback: {traceback_str}")
            return None
        except Exception as e:
            logger.error(f"💥 Unexpected error creating product: {e}")
            import traceback
            traceback_str = traceback.format_exc()
            logger.error(f"📋 Traceback: {traceback_str}")
            return None
    
    def get_products_by_seller(self, seller_id: int) -> List[Product]:
        """Get all products for a seller"""
        try:
            with self.get_session() as session:
                return session.query(Product).filter(
                    Product.seller_id == seller_id,
                    Product.is_active == True
                ).all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get products for seller_id {seller_id}: {e}")
            return []
    
    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID"""
        try:
            with self.get_session() as session:
                return session.query(Product).filter(Product.id == product_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get product by id {product_id}: {e}")
            return None
    
    def update_product(self, product_id: int, **kwargs) -> Optional[Product]:
        """Update product information"""
        try:
            with self.get_session() as session:
                product = session.query(Product).filter(Product.id == product_id).first()
                if product:
                    for key, value in kwargs.items():
                        if hasattr(product, key) and value is not None:
                            setattr(product, key, value)
                    session.commit()
                    session.refresh(product)
                    logger.info(f"Updated product id: {product_id}")
                return product
        except SQLAlchemyError as e:
            logger.error(f"Failed to update product: {e}")
            return None
    
    # Migration helper methods
    def migrate_json_data(self, json_file_path: str, telegram_id: int) -> bool:
        """Migrate data from JSON files to database"""
        import json
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Get or create seller
            seller = self.get_seller_by_telegram_id(telegram_id)
            if not seller:
                seller = self.create_seller(f"User_{telegram_id}", telegram_id=telegram_id)
                if not seller:
                    return False
            
            # Create product
            product = self.create_product(
                seller_id=seller.id,
                product_name=data.get('product_name', 'Unknown Product'),
                price=data.get('price', 0),
                description=data.get('description', ''),
                local_image_path=data.get('local_image_path'),
                specifications=data.get('specifications', {})
            )
            
            return product is not None
            
        except Exception as e:
            logger.error(f"Failed to migrate JSON data from {json_file_path}: {e}")
            return False
