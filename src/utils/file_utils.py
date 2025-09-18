"""File operation utilities for CraftBuddy bot"""
import os
import time
from typing import Optional, Tuple
from src.utils.logger import get_logger

logger = get_logger(__name__)

def ensure_directory(directory: str) -> None:
    """Ensure directory exists, create if it doesn't"""
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")

def save_image_file(
    file_content: bytes,
    chat_id: int,
    file_extension: str = ".jpg",
    image_dir: str = "product_images"
) -> str:
    """
    Save image file to local storage
    
    Args:
        file_content: Binary image data
        chat_id: Telegram chat ID
        file_extension: File extension (with dot)
        image_dir: Directory to save images
    
    Returns:
        Path to saved image file
    """
    ensure_directory(image_dir)
    
    # Generate unique filename
    timestamp = int(time.time())
    filename = f"chat_{chat_id}_product_image_{timestamp}{file_extension}"
    file_path = os.path.join(image_dir, filename)
    
    try:
        with open(file_path, "wb") as f:
            f.write(file_content)
        logger.info(f"Image saved to: {file_path}")
        return file_path
    except IOError as e:
        logger.error(f"Failed to save image: {e}")
        raise

def get_file_extension_from_path(file_path: str) -> str:
    """
    Get file extension from path, default to .jpg if none found
    
    Args:
        file_path: File path
        
    Returns:
        File extension with dot (e.g., '.jpg')
    """
    extension = os.path.splitext(file_path)[1]
    return extension if extension else ".jpg"

def sanitize_file_path(file_path: str) -> str:
    """
    Sanitize file path for URL usage (convert backslashes to forward slashes)
    
    Args:
        file_path: Original file path
        
    Returns:
        Sanitized file path
    """
    return file_path.replace('\\', '/')

def file_exists(file_path: str) -> bool:
    """Check if file exists"""
    return os.path.exists(file_path)

def get_file_size(file_path: str) -> Optional[int]:
    """
    Get file size in bytes
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in bytes or None if file doesn't exist
    """
    try:
        return os.path.getsize(file_path)
    except OSError:
        return None

def cleanup_old_files(
    directory: str,
    max_age_seconds: int = 7 * 24 * 60 * 60,  # 7 days
    file_pattern: Optional[str] = None
) -> int:
    """
    Clean up old files in directory
    
    Args:
        directory: Directory to clean
        max_age_seconds: Maximum age of files to keep
        file_pattern: Optional pattern to match files (e.g., "*.jpg")
        
    Returns:
        Number of files deleted
    """
    if not os.path.exists(directory):
        return 0
    
    current_time = time.time()
    deleted_count = 0
    
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            if not os.path.isfile(file_path):
                continue
                
            # Check file pattern if specified
            if file_pattern and not filename.endswith(file_pattern.replace("*", "")):
                continue
                
            # Check file age
            file_age = current_time - os.path.getmtime(file_path)
            if file_age > max_age_seconds:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    logger.info(f"Deleted old file: {file_path}")
                except OSError as e:
                    logger.error(f"Failed to delete file {file_path}: {e}")
                    
    except OSError as e:
        logger.error(f"Failed to clean directory {directory}: {e}")
    
    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} old files from {directory}")
    
    return deleted_count
