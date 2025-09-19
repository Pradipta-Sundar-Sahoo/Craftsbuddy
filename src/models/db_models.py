"""SQLAlchemy database models for CraftsBuddy"""
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, TIMESTAMP, ForeignKey, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func
from typing import Dict, Any
import json

Base = declarative_base()

class Seller(Base):
    """Seller/Artisan information"""
    __tablename__ = 'sellers'
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    brand_name = Column(String(255))
    phone_number = Column(String(20))
    address = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    products = relationship("Product", back_populates="seller", cascade="all, delete-orphan")

class Product(Base):
    """Product information"""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    seller_id = Column(Integer, ForeignKey('sellers.id'), nullable=False)
    product_name = Column(String(500), nullable=False)
    price = Column(Integer, nullable=False, default=0)  # Price in smallest currency unit
    description = Column(Text)
    local_image_path = Column(String(500))  # For migration compatibility
    cloud_image_url = Column(String(1000))  # Google Cloud Storage URL
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    seller = relationship("Seller", back_populates="products")
    specifications = relationship("ProductSpecification", back_populates="product", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "product_name": self.product_name,
            "price": self.price,
            "description": self.description,
            "local_image_path": self.local_image_path,
            "cloud_image_url": self.cloud_image_url,
            "specifications": {spec.spec_key: spec.spec_value for spec in self.specifications},
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class ProductSpecification(Base):
    """Product specifications - flexible key-value storage"""
    __tablename__ = 'product_specifications'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    spec_key = Column(String(255), nullable=False)
    spec_value = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    product = relationship("Product", back_populates="specifications")
    
    # Unique constraint
    __table_args__ = (
        {'schema': None},
    )

# Database configuration
class DatabaseConfig:
    """Database configuration and session management"""
    
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all tables"""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self):
        """Get database session"""
        return self.SessionLocal()
