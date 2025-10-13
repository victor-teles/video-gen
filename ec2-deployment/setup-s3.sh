#!/bin/bash

# S3 Setup Script for Editur AI Backend
# This script creates and configures S3 bucket for video storage

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured. Run: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=${AWS_DEFAULT_REGION:-us-east-1}

log_info "Setting up S3 for AWS Account: $ACCOUNT_ID"
log_info "Region: $REGION"

# Generate unique bucket name
BUCKET_NAME="editur-ai-storage-$(date +%s)-$(echo $ACCOUNT_ID | tail -c 5)"

log_info "Creating S3 bucket: $BUCKET_NAME"

# Create bucket
aws s3 mb s3://$BUCKET_NAME --region $REGION

if [ $? -eq 0 ]; then
    log_success "S3 bucket created successfully"
else
    log_error "Failed to create S3 bucket"
    exit 1
fi

# Create CORS policy
log_info "Setting up CORS policy..."
cat > cors-policy.json << EOF
{
  "CORSRules": [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET", "POST", "PUT", "DELETE", "HEAD"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3000,
      "ExposeHeaders": ["ETag"]
    }
  ]
}
EOF

aws s3api put-bucket-cors \
    --bucket $BUCKET_NAME \
    --cors-configuration file://cors-policy.json

# Create lifecycle policy to save costs
log_info "Setting up lifecycle policy for cost optimization..."
cat > lifecycle-policy.json << EOF
{
  "Rules": [
    {
      "ID": "DeleteOldUploads",
      "Status": "Enabled",
      "Filter": {"Prefix": "uploads/"},
      "Expiration": {"Days": 7}
    },
    {
      "ID": "ArchiveOldResults", 
      "Status": "Enabled",
      "Filter": {"Prefix": "results/"},
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "GLACIER"
        }
      ]
    },
    {
      "ID": "DeleteOldProcessing",
      "Status": "Enabled", 
      "Filter": {"Prefix": "processing/"},
      "Expiration": {"Days": 1}
    }
  ]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
    --bucket $BUCKET_NAME \
    --lifecycle-configuration file://lifecycle-policy.json

# Set up bucket versioning (optional, for safety)
log_info "Enabling bucket versioning..."
aws s3api put-bucket-versioning \
    --bucket $BUCKET_NAME \
    --versioning-configuration Status=Enabled

# Set up server-side encryption
log_info "Enabling server-side encryption..."
aws s3api put-bucket-encryption \
    --bucket $BUCKET_NAME \
    --server-side-encryption-configuration '{
        "Rules": [
            {
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }
        ]
    }'

# Block public access (security)
log_info "Configuring security settings..."
aws s3api put-public-access-block \
    --bucket $BUCKET_NAME \
    --public-access-block-configuration \
        BlockPublicAcls=true,\
        IgnorePublicAcls=true,\
        BlockPublicPolicy=false,\
        RestrictPublicBuckets=false

# Create bucket policy for the application
log_info "Setting up bucket policy..."
cat > bucket-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowEditurAIAccess",
      "Effect": "Allow",
      "Principal": "*",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::$BUCKET_NAME/*",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "$ACCOUNT_ID"
        }
      }
    }
  ]
}
EOF

aws s3api put-bucket-policy \
    --bucket $BUCKET_NAME \
    --policy file://bucket-policy.json

# Test bucket access
log_info "Testing bucket access..."
echo "test" > test-file.txt
aws s3 cp test-file.txt s3://$BUCKET_NAME/test-file.txt

if aws s3 ls s3://$BUCKET_NAME/test-file.txt > /dev/null; then
    log_success "Bucket access test successful"
    aws s3 rm s3://$BUCKET_NAME/test-file.txt
    rm test-file.txt
else
    log_error "Bucket access test failed"
fi

# Clean up temporary files
rm -f cors-policy.json lifecycle-policy.json bucket-policy.json

# Output configuration
log_success "S3 setup complete!"
echo ""
echo "📋 S3 Configuration:"
echo "   Bucket Name: $BUCKET_NAME"
echo "   Region: $REGION"
echo "   Encryption: AES256"
echo "   Lifecycle: Enabled (cost optimization)"
echo "   CORS: Configured for web uploads"
echo ""
echo "🔧 Environment Configuration:"
echo "   Add this to your .env file:"
echo ""
echo "   S3_BUCKET_NAME=$BUCKET_NAME"
echo "   AWS_REGION=$REGION"
echo ""
echo "💡 Next Steps:"
echo "   1. Update your .env file with the bucket name above"
echo "   2. Restart your services: sudo systemctl restart editur-api editur-worker"
echo "   3. Test video upload through your API"
echo ""
echo "💰 Cost Optimization Features:"
echo "   ✅ Automatic deletion of uploads after 7 days"
echo "   ✅ Archive old results to Glacier after 30 days" 
echo "   ✅ Delete temporary processing files after 1 day"
echo "   ✅ Server-side encryption enabled"
echo ""

# Save bucket info
cat > s3-info.json << EOF
{
  "bucket_name": "$BUCKET_NAME",
  "region": "$REGION", 
  "account_id": "$ACCOUNT_ID",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "features": {
    "cors": true,
    "lifecycle": true,
    "encryption": true,
    "versioning": true
  }
}
EOF

log_success "S3 configuration saved to s3-info.json"