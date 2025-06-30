"""
Storage Handler for Video Clip Generator
Manages both local and S3 storage based on configuration
"""
import os
import shutil
from pathlib import Path
from typing import Optional, List, Tuple, Union
import logging
import boto3
from botocore.exceptions import ClientError
import mimetypes
import config

class StorageHandler:
    def __init__(self):
        """Initialize storage handler based on configuration"""
        self.storage_type = config.STORAGE_TYPE
        self.logger = logging.getLogger(__name__)
        
        # Debug logging
        self.logger.info(f"🔧 StorageHandler: STORAGE_TYPE = '{self.storage_type}'")
        
        if self.storage_type == 's3':
            self.logger.info("🔧 StorageHandler: Initializing S3 client...")
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
                region_name=config.AWS_REGION
            )
            self.bucket_name = config.S3_BUCKET_NAME
            self.logger.info(f"✅ StorageHandler: S3 client initialized for bucket '{self.bucket_name}'")
        else:
            self.logger.info("🔧 StorageHandler: Using local storage")
            self.s3_client = None
            self.bucket_name = None
    
    def _get_s3_key(self, file_path: Union[str, Path]) -> str:
        """Convert local path to S3 key"""
        path = Path(file_path)
        if 'uploads' in str(path):
            return f"uploads/{path.name}"
        elif 'processing' in str(path):
            return f"processing/{path.name}"
        elif 'results' in str(path):
            return f"results/{path.name}"
        return str(path.name)
    
    def save_file(self, source_path: Union[str, Path], dest_path: Union[str, Path]) -> bool:
        """
        Save a file to storage
        
        Args:
            source_path: Path to source file
            dest_path: Destination path/key
            
        Returns:
            bool: True if successful
        """
        try:
            if self.storage_type == 's3':
                s3_key = self._get_s3_key(dest_path)
                content_type = mimetypes.guess_type(source_path)[0]
                extra_args = {'ContentType': content_type} if content_type else {}
                self.s3_client.upload_file(str(source_path), self.bucket_name, s3_key, ExtraArgs=extra_args)
                return True
            else:
                shutil.copy2(source_path, dest_path)
                return True
        except Exception as e:
            self.logger.error(f"Failed to save file {source_path} to {dest_path}: {e}")
            return False
    
    def get_file(self, file_path: Union[str, Path], local_path: Union[str, Path]) -> bool:
        """
        Get a file from storage
        
        Args:
            file_path: Path/key to file in storage
            local_path: Local path to save file
            
        Returns:
            bool: True if successful
        """
        try:
            if self.storage_type == 's3':
                s3_key = self._get_s3_key(file_path)
                Path(local_path).parent.mkdir(parents=True, exist_ok=True)
                self.s3_client.download_file(self.bucket_name, s3_key, str(local_path))
                return True
            else:
                shutil.copy2(file_path, local_path)
                return True
        except Exception as e:
            self.logger.error(f"Failed to get file {file_path} to {local_path}: {e}")
            return False
    
    def delete_file(self, file_path: Union[str, Path]) -> bool:
        """
        Delete a file from storage
        
        Args:
            file_path: Path/key to file
            
        Returns:
            bool: True if successful
        """
        try:
            if self.storage_type == 's3':
                s3_key = self._get_s3_key(file_path)
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
                return True
            else:
                os.remove(file_path)
                return True
        except Exception as e:
            self.logger.error(f"Failed to delete file {file_path}: {e}")
            return False
    
    def move_file(self, source_path: Union[str, Path], dest_path: Union[str, Path]) -> bool:
        """
        Move a file within storage
        
        Args:
            source_path: Current path/key
            dest_path: New path/key
            
        Returns:
            bool: True if successful
        """
        try:
            if self.storage_type == 's3':
                source_key = self._get_s3_key(source_path)
                dest_key = self._get_s3_key(dest_path)
                # Copy the object
                self.s3_client.copy_object(
                    Bucket=self.bucket_name,
                    CopySource={'Bucket': self.bucket_name, 'Key': source_key},
                    Key=dest_key
                )
                # Delete the original
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=source_key)
                return True
            else:
                shutil.move(source_path, dest_path)
                return True
        except Exception as e:
            self.logger.error(f"Failed to move file {source_path} to {dest_path}: {e}")
            return False
    
    def list_files(self, directory: Union[str, Path]) -> List[Tuple[str, int]]:
        """
        List files in directory
        
        Args:
            directory: Directory path/prefix
            
        Returns:
            List[Tuple[str, int]]: List of (file_path, size) tuples
        """
        try:
            if self.storage_type == 's3':
                prefix = self._get_s3_key(directory)
                paginator = self.s3_client.get_paginator('list_objects_v2')
                files = []
                for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            files.append((obj['Key'], obj['Size']))
                return files
            else:
                files = []
                for path in Path(directory).glob('*'):
                    if path.is_file():
                        files.append((str(path), path.stat().st_size))
                return files
        except Exception as e:
            self.logger.error(f"Failed to list files in {directory}: {e}")
            return []
    
    def get_file_url(self, file_path: Union[str, Path], expires_in: int = 3600) -> Optional[str]:
        """
        Get URL for file (S3 presigned URL or local file path)
        
        Args:
            file_path: Path to file
            expires_in: URL expiration time in seconds (S3 only)
            
        Returns:
            Optional[str]: File URL or None if failed
        """
        try:
            if self.storage_type == 's3':
                s3_key = self._get_s3_key(file_path)
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.bucket_name,
                        'Key': s3_key
                    },
                    ExpiresIn=expires_in
                )
                return url
            else:
                return str(file_path) if os.path.exists(file_path) else None
        except Exception as e:
            self.logger.error(f"Failed to get URL for {file_path}: {e}")
            return None