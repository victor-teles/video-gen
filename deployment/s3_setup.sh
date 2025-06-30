#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Setting up S3 bucket for Video Clip Generator...${NC}"

# Load environment variables
if [ -f "../.env" ]; then
    source ../.env
else
    echo -e "${RED}❌ .env file not found${NC}"
    exit 1
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if required environment variables are set
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ] || [ -z "$AWS_REGION" ]; then
    echo -e "${RED}❌ AWS credentials not found in .env file${NC}"
    echo "Please ensure you have the following in your .env file:"
    echo "AWS_ACCESS_KEY_ID=your_access_key"
    echo "AWS_SECRET_ACCESS_KEY=your_secret_key"
    echo "AWS_REGION=your_region (e.g., us-east-1)"
    exit 1
fi

# Set bucket name
BUCKET_NAME=${S3_BUCKET_NAME:-"trod-video-clips"}

echo -e "${YELLOW}📦 Creating S3 bucket: $BUCKET_NAME${NC}"

# Create S3 bucket
aws s3api create-bucket \
    --bucket $BUCKET_NAME \
    --region $AWS_REGION \
    $(if [ "$AWS_REGION" != "us-east-1" ]; then echo "--create-bucket-configuration LocationConstraint=$AWS_REGION"; fi)

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to create bucket${NC}"
    exit 1
fi

# Enable versioning
echo -e "${YELLOW}🔄 Enabling versioning...${NC}"
aws s3api put-bucket-versioning \
    --bucket $BUCKET_NAME \
    --versioning-configuration Status=Enabled

# Create CORS configuration file
echo -e "${YELLOW}🔑 Setting up CORS policy...${NC}"
cat > cors.json << EOF
{
    "CORSRules": [
        {
            "AllowedHeaders": ["*"],
            "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
            "AllowedOrigins": ["https://trod.ai", "https://api.trod.ai", "http://localhost:3000", "http://localhost:8000"],
            "ExposeHeaders": ["ETag", "x-amz-server-side-encryption"],
            "MaxAgeSeconds": 3000
        }
    ]
}
EOF

# Apply CORS configuration
aws s3api put-bucket-cors \
    --bucket $BUCKET_NAME \
    --cors-configuration file://cors.json

# Create bucket structure
echo -e "${YELLOW}📁 Creating bucket structure...${NC}"

# Create empty files to establish folder structure
touch temp_file
aws s3 cp temp_file s3://$BUCKET_NAME/uploads/.keep
aws s3 cp temp_file s3://$BUCKET_NAME/processing/.keep
aws s3 cp temp_file s3://$BUCKET_NAME/results/.keep
rm temp_file

# Create lifecycle policy for cleanup
echo -e "${YELLOW}⚙️ Setting up lifecycle policies...${NC}"
cat > lifecycle.json << EOF
{
    "Rules": [
        {
            "ID": "CleanupRule",
            "Status": "Enabled",
            "Filter": {
                "Prefix": "uploads/"
            },
            "Expiration": {
                "Days": 1
            }
        },
        {
            "ID": "ProcessingCleanup",
            "Status": "Enabled",
            "Filter": {
                "Prefix": "processing/"
            },
            "Expiration": {
                "Days": 1
            }
        },
        {
            "ID": "ResultsCleanup",
            "Status": "Enabled",
            "Filter": {
                "Prefix": "results/"
            },
            "Expiration": {
                "Days": 7
            }
        }
    ]
}
EOF

# Apply lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
    --bucket $BUCKET_NAME \
    --lifecycle-configuration file://lifecycle.json

# Clean up temporary files
rm cors.json lifecycle.json

echo -e "${GREEN}✅ S3 bucket setup complete!${NC}"
echo -e "${GREEN}📁 Bucket structure:${NC}"
echo -e "  s3://$BUCKET_NAME/"
echo -e "  ├── uploads/     (temporary storage for uploaded videos)"
echo -e "  ├── processing/  (temporary storage for videos being processed)"
echo -e "  └── results/     (storage for generated clips and captions)"
echo
echo -e "${YELLOW}ℹ️  Lifecycle policies:${NC}"
echo -e "  • uploads/: deleted after 1 day"
echo -e "  • processing/: deleted after 1 day"
echo -e "  • results/: deleted after 7 days" 