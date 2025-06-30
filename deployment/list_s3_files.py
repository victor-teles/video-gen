"""
List files in S3 bucket for Video Clip Generator
"""
import os
import sys
from pathlib import Path
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Add parent directory to path for importing config
sys.path.append(str(Path(__file__).parent.parent))
import config

def format_size(size_bytes):
    """Format file size in bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"

def format_date(timestamp):
    """Format timestamp to readable date"""
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")

def list_s3_contents():
    """List all files in S3 bucket"""
    try:
        # Initialize S3 client
        s3 = boto3.client('s3',
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            region_name=config.AWS_REGION
        )
        
        print(f"\n📂 S3 Bucket: {config.S3_BUCKET_NAME}")
        print("=" * 80)
        
        # List objects by prefix (folder)
        for prefix in ['uploads/', 'processing/', 'results/']:
            print(f"\n📁 {prefix}")
            print("-" * 80)
            print(f"{'Last Modified':<20} {'Size':<10} {'File Name':<50}")
            print("-" * 80)
            
            try:
                paginator = s3.get_paginator('list_objects_v2')
                total_size = 0
                count = 0
                
                for page in paginator.paginate(Bucket=config.S3_BUCKET_NAME, Prefix=prefix):
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            # Skip the folder itself
                            if obj['Key'] == prefix:
                                continue
                                
                            file_name = obj['Key'].replace(prefix, '')
                            if file_name:  # Skip empty file names
                                size = format_size(obj['Size'])
                                date = format_date(obj['LastModified'])
                                print(f"{date:<20} {size:<10} {file_name:<50}")
                                
                                total_size += obj['Size']
                                count += 1
                
                if count == 0:
                    print("(empty)")
                else:
                    print("-" * 80)
                    print(f"Total: {count} files, Size: {format_size(total_size)}")
            
            except ClientError as e:
                print(f"Error listing {prefix}: {str(e)}")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if "NoCredentialsError" in str(e):
            print("\n⚠️  Please check your AWS credentials in .env file:")
            print("   AWS_ACCESS_KEY_ID=your_access_key")
            print("   AWS_SECRET_ACCESS_KEY=your_secret_key")
            print("   AWS_REGION=your_region")
            print("   S3_BUCKET_NAME=your_bucket_name")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    list_s3_contents() 