"""File storage abstraction for datasets - supports MinIO and AWS S3.

Provides a unified interface for uploading, downloading, and deleting files
regardless of whether MinIO or S3 is used as the backend.
"""
import os
import logging
from typing import BinaryIO, Optional
from datetime import datetime, timedelta
from .config import settings

logger = logging.getLogger(__name__)


class FileStorageProvider:
    """Abstract base for file storage providers."""
    
    def upload(self, file_path: str, data: bytes, metadata: dict = None) -> str:
        """Upload file and return storage path."""
        raise NotImplementedError
    
    def download(self, file_path: str) -> bytes:
        """Download file by path."""
        raise NotImplementedError
    
    def delete(self, file_path: str) -> bool:
        """Delete file by path."""
        raise NotImplementedError
    
    def get_download_url(self, file_path: str, expiration_hours: int = 24) -> str:
        """Generate a temporary download URL."""
        raise NotImplementedError


class LocalStorageProvider(FileStorageProvider):
    """Local filesystem storage (development only)."""
    
    def __init__(self, base_path: str = None):
        self.base_path = base_path or os.path.join(os.path.expanduser("~"), ".dataverse", "storage")
        os.makedirs(self.base_path, exist_ok=True)
        logger.info(f"[LocalStorage] Initialized at {self.base_path}")
    
    def upload(self, file_path: str, data: bytes, metadata: dict = None) -> str:
        """Save file locally."""
        full_path = os.path.join(self.base_path, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'wb') as f:
            f.write(data)
        
        logger.info(f"[LocalStorage] Uploaded {file_path} ({len(data)} bytes)")
        return file_path
    
    def download(self, file_path: str) -> bytes:
        """Read file locally."""
        full_path = os.path.join(self.base_path, file_path)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(full_path, 'rb') as f:
            return f.read()
    
    def delete(self, file_path: str) -> bool:
        """Delete file locally."""
        full_path = os.path.join(self.base_path, file_path)
        
        if os.path.exists(full_path):
            os.remove(full_path)
            logger.info(f"[LocalStorage] Deleted {file_path}")
            return True
        return False
    
    def get_download_url(self, file_path: str, expiration_hours: int = 24) -> str:
        """Local storage doesn't support URLs - return file path."""
        return f"/api/files/download?path={file_path}"


class MinIOStorageProvider(FileStorageProvider):
    """MinIO S3-compatible object storage."""
    
    def __init__(self):
        try:
            from minio import Minio
            from minio.error import S3Error
        except ImportError:
            raise ImportError("MinIO client not installed. Install with: pip install minio")
        
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.bucket = settings.MINIO_BUCKET
        
        # Ensure bucket exists
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket, location="us-east-1")
                logger.info(f"[MinIO] Created bucket: {self.bucket}")
        except Exception as e:
            logger.warning(f"[MinIO] Could not verify bucket: {e}")
        
        logger.info(f"[MinIO] Initialized with endpoint {settings.MINIO_ENDPOINT}")
    
    def upload(self, file_path: str, data: bytes, metadata: dict = None) -> str:
        """Upload file to MinIO."""
        try:
            from minio.api import ObjectDoesNotExistError
        except ImportError:
            raise ImportError("MinIO client not installed")
        
        try:
            self.client.put_object(
                self.bucket,
                file_path,
                data,
                len(data),
                content_type="application/octet-stream",
                metadata=metadata,
            )
            
            logger.info(f"[MinIO] Uploaded {file_path} ({len(data)} bytes)")
            return file_path
            
        except Exception as e:
            logger.error(f"[MinIO] Upload failed for {file_path}: {e}")
            raise
    
    def download(self, file_path: str) -> bytes:
        """Download file from MinIO."""
        try:
            response = self.client.get_object(self.bucket, file_path)
            data = response.read()
            response.close()
            return data
            
        except Exception as e:
            logger.error(f"[MinIO] Download failed for {file_path}: {e}")
            raise
    
    def delete(self, file_path: str) -> bool:
        """Delete file from MinIO."""
        try:
            self.client.remove_object(self.bucket, file_path)
            logger.info(f"[MinIO] Deleted {file_path}")
            return True
            
        except Exception as e:
            logger.warning(f"[MinIO] Delete failed for {file_path}: {e}")
            return False
    
    def get_download_url(self, file_path: str, expiration_hours: int = 24) -> str:
        """Generate temporary download URL for MinIO."""
        try:
            from datetime import timedelta
            
            url = self.client.get_presigned_download_url(
                self.bucket,
                file_path,
                expires=timedelta(hours=expiration_hours),
            )
            return url
            
        except Exception as e:
            logger.error(f"[MinIO] URL generation failed: {e}")
            return f"/api/files/download?path={file_path}"


class S3StorageProvider(FileStorageProvider):
    """AWS S3 storage."""
    
    def __init__(self):
        try:
            import boto3
        except ImportError:
            raise ImportError("boto3 not installed. Install with: pip install boto3")
        
        self.client = boto3.client(
            's3',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        self.bucket = settings.AWS_S3_BUCKET
        
        logger.info(f"[S3] Initialized with bucket {self.bucket} in {settings.AWS_REGION}")
    
    def upload(self, file_path: str, data: bytes, metadata: dict = None) -> str:
        """Upload file to S3."""
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=file_path,
                Body=data,
                Metadata=metadata or {},
            )
            
            logger.info(f"[S3] Uploaded {file_path} ({len(data)} bytes)")
            return file_path
            
        except Exception as e:
            logger.error(f"[S3] Upload failed: {e}")
            raise
    
    def download(self, file_path: str) -> bytes:
        """Download file from S3."""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=file_path)
            return response['Body'].read()
            
        except Exception as e:
            logger.error(f"[S3] Download failed: {e}")
            raise
    
    def delete(self, file_path: str) -> bool:
        """Delete file from S3."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=file_path)
            logger.info(f"[S3] Deleted {file_path}")
            return True
            
        except Exception as e:
            logger.warning(f"[S3] Delete failed: {e}")
            return False
    
    def get_download_url(self, file_path: str, expiration_hours: int = 24) -> str:
        """Generate temporary download URL for S3."""
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': file_path},
                ExpiresIn=expiration_hours * 3600,
            )
            return url
            
        except Exception as e:
            logger.error(f"[S3] URL generation failed: {e}")
            return f"/api/files/download?path={file_path}"


# Factory function to create appropriate provider
def get_storage_provider() -> FileStorageProvider:
    """Get configured storage provider based on settings."""
    
    storage_type = settings.STORAGE_TYPE.lower()
    
    if storage_type == "minio":
        return MinIOStorageProvider()
    elif storage_type == "s3":
        return S3StorageProvider()
    else:  # local (default)
        return LocalStorageProvider()


# Global instance
_storage_provider = None


def init_storage():
    """Initialize the global storage provider."""
    global _storage_provider
    _storage_provider = get_storage_provider()


def get_storage() -> FileStorageProvider:
    """Get the global storage provider instance."""
    if _storage_provider is None:
        init_storage()
    return _storage_provider
