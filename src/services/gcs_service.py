"""Google Cloud Storage service for handling image uploads"""
import os
import time
from typing import Optional, Tuple
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
from src.utils.logger import get_logger
from src.config.settings import config

logger = get_logger(__name__)

class GCSService:
    """Google Cloud Storage service for image uploads"""
    
    def __init__(self, bucket_name: str, credentials_path: Optional[str] = None):
        """
        Initialize GCS service
        
        Args:
            bucket_name: GCS bucket name
            credentials_path: Path to service account credentials JSON file
        """
        self.bucket_name = bucket_name
        
        try:
            if credentials_path and os.path.exists(credentials_path):
                # Use service account credentials file
                self.client = storage.Client.from_service_account_json(credentials_path)
            else:
                # Use default credentials (environment variables or metadata server)
                self.client = storage.Client()
            
            self.bucket = self.client.bucket(bucket_name)
            logger.info(f"GCS service initialized with bucket: {bucket_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize GCS service: {e}")
            raise
    
    def upload_image(
        self,
        file_content: bytes,
        chat_id: int,
        file_extension: str = ".jpg",
        folder: str = "product-images"
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Upload image to Google Cloud Storage
        
        Args:
            file_content: Binary image data
            chat_id: Telegram chat ID
            file_extension: File extension (with dot)
            folder: Folder name in GCS bucket
            
        Returns:
            Tuple of (success, public_url, error_message)
        """
        logger.info(f"🔄 Starting GCS upload for chat {chat_id}")
        logger.info(f"📄 File extension: {file_extension}")
        logger.info(f"📁 Folder: {folder}")
        logger.info(f"📦 File size: {len(file_content)} bytes")
        
        try:
            # Generate unique filename
            timestamp = int(time.time())
            filename = f"{folder}/chat_{chat_id}_product_image_{timestamp}{file_extension}"
            logger.info(f"📝 Generated filename: {filename}")
            
            # Create blob and upload
            logger.info(f"🔄 Creating blob in bucket: {self.bucket_name}")
            blob = self.bucket.blob(filename)
            
            content_type = self._get_content_type(file_extension)
            logger.info(f"📋 Content type: {content_type}")
            
            logger.info(f"⬆️  Uploading to GCS...")
            blob.upload_from_string(
                file_content,
                content_type=content_type
            )
            logger.info(f"✅ Upload completed successfully")
            
            # Try to make blob publicly readable
            logger.info(f"🔓 Making blob public...")
            try:
                blob.make_public()
                logger.info("✅ Image made public using legacy ACL")
            except Exception as e:
                logger.warning(f"⚠️  Could not make image public using legacy ACL: {e}")
                logger.info("📝 Image uploaded but may not be publicly accessible (uniform bucket-level access enabled)")
            
            public_url = blob.public_url
            logger.info(f"🌐 Public URL generated: {public_url}")
            
            return True, public_url, None
            
        except GoogleCloudError as e:
            logger.error(f"❌ GCS upload error: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return False, None, f"Cloud storage error: {str(e)}"
        except Exception as e:
            logger.error(f"💥 Unexpected error during upload: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return False, None, f"Upload failed: {str(e)}"
    
    def delete_image(self, image_url: str) -> bool:
        """
        Delete image from GCS using its public URL
        
        Args:
            image_url: Public URL of the image
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Extract blob name from public URL
            blob_name = self._extract_blob_name_from_url(image_url)
            if not blob_name:
                logger.error(f"Could not extract blob name from URL: {image_url}")
                return False
            
            blob = self.bucket.blob(blob_name)
            blob.delete()
            
            logger.info(f"Image deleted from GCS: {blob_name}")
            return True
            
        except GoogleCloudError as e:
            logger.error(f"Failed to delete image from GCS: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during delete: {e}")
            return False
    
    def _get_content_type(self, file_extension: str) -> str:
        """
        Get content type based on file extension
        
        Args:
            file_extension: File extension with dot
            
        Returns:
            MIME content type
        """
        extension_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        return extension_map.get(file_extension.lower(), 'image/jpeg')
    
    def _extract_blob_name_from_url(self, public_url: str) -> Optional[str]:
        """
        Extract blob name from GCS public URL
        
        Args:
            public_url: GCS public URL
            
        Returns:
            Blob name or None if extraction failed
        """
        try:
            # GCS public URLs format: https://storage.googleapis.com/bucket-name/blob-name
            if 'storage.googleapis.com' in public_url:
                parts = public_url.split(f'/{self.bucket_name}/')
                if len(parts) == 2:
                    return parts[1]
            return None
        except Exception:
            return None
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test GCS connection and bucket access
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Try to get bucket info
            bucket_info = self.client.get_bucket(self.bucket_name)
            return True, f"Successfully connected to bucket: {bucket_info.name}"
            
        except GoogleCloudError as e:
            return False, f"Failed to connect to GCS: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
