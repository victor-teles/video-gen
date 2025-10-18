"""
S3 Storage Handler for Video Clip Generator
"""
import os
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
import mimetypes
import logging
from typing import Optional, List, Tuple

class S3Storage:
    def __init__(self):
        """Initialize S3 storage handler"""
        self.endpoint_url = os.getenv('S3_ENDPOINT_URL', 'https://s3.us-east-1.amazonaws.com')
        self.s3_client = boto3.client('s3', endpoint_url=self.endpoint_url)
        self.bucket_name = os.getenv('S3_BUCKET_NAME', 'trod-video-clips')
        self.logger = logging.getLogger(__name__)

    def upload_file(self, local_path: str, s3_key: str) -> bool:
        """
        Upload a file to S3
        
        Args:
            local_path (str): Path to local file
            s3_key (str): S3 key (path) where file will be stored
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Guess content type
            content_type = mimetypes.guess_type(local_path)[0]
            extra_args = {'ContentType': content_type} if content_type else {}
            
            # Upload file
            self.s3_client.upload_file(
                local_path, 
                self.bucket_name, 
                s3_key,
                ExtraArgs=extra_args
            )
            
            self.logger.info(f"✅ Uploaded {local_path} to s3://{self.bucket_name}/{s3_key}")
            return True
            
        except ClientError as e:
            self.logger.error(f"❌ Failed to upload {local_path}: {e}")
            return False

    def download_file(self, s3_key: str, local_path: str) -> bool:
        """
        Download a file from S3
        
        Args:
            s3_key (str): S3 key (path) to download
            local_path (str): Local path to save file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Download file
            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                local_path
            )
            
            self.logger.info(f"✅ Downloaded s3://{self.bucket_name}/{s3_key} to {local_path}")
            return True
            
        except ClientError as e:
            self.logger.error(f"❌ Failed to download {s3_key}: {e}")
            return False

    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3
        
        Args:
            s3_key (str): S3 key (path) to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            self.logger.info(f"✅ Deleted s3://{self.bucket_name}/{s3_key}")
            return True
            
        except ClientError as e:
            self.logger.error(f"❌ Failed to delete {s3_key}: {e}")
            return False

    def list_files(self, prefix: str = "") -> List[Tuple[str, int]]:
        """
        List files in S3 bucket with given prefix
        
        Args:
            prefix (str): Prefix to filter files (folder path)
            
        Returns:
            List[Tuple[str, int]]: List of (file_key, size) tuples
        """
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            files = []
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        files.append((obj['Key'], obj['Size']))
            
            return files
            
        except ClientError as e:
            self.logger.error(f"❌ Failed to list files with prefix {prefix}: {e}")
            return []

    def get_presigned_url(self, s3_key: str, expires_in: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for file download
        
        Args:
            s3_key (str): S3 key (path) to generate URL for
            expires_in (int): URL expiration time in seconds
            
        Returns:
            Optional[str]: Presigned URL or None if failed
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expires_in
            )
            return url
            
        except ClientError as e:
            self.logger.error(f"❌ Failed to generate presigned URL for {s3_key}: {e}")
            return None

    def move_file(self, source_key: str, dest_key: str) -> bool:
        """
        Move/rename a file within the S3 bucket
        
        Args:
            source_key (str): Current S3 key
            dest_key (str): New S3 key
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Copy the object
            self.s3_client.copy_object(
                Bucket=self.bucket_name,
                CopySource={'Bucket': self.bucket_name, 'Key': source_key},
                Key=dest_key
            )
            
            # Delete the original
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=source_key
            )
            
            self.logger.info(f"✅ Moved s3://{self.bucket_name}/{source_key} to s3://{self.bucket_name}/{dest_key}")
            return True
            
        except ClientError as e:
            self.logger.error(f"❌ Failed to move {source_key} to {dest_key}: {e}")
            return False 