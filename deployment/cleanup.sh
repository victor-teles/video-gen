#!/bin/bash

set -e

# Configuration
PROJECT_NAME="video-clip-generator"
ENVIRONMENT="production"
AWS_REGION="us-east-1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${RED}🧹 Video Clip Generator - AWS Cleanup Script${NC}"
echo -e "${RED}=============================================${NC}"

echo -e "\n${YELLOW}⚠️  WARNING: This will delete ALL AWS resources for the project!${NC}"
echo -e "${YELLOW}This includes:${NC}"
echo -e "${YELLOW}  • ECS Cluster and Services${NC}"
echo -e "${YELLOW}  • Load Balancer${NC}"
echo -e "${YELLOW}  • VPC and Networking${NC}"
echo -e "${YELLOW}  • ECR Repositories and Docker Images${NC}"
echo -e "${YELLOW}  • Redis Cluster${NC}"
echo -e "${YELLOW}  • CloudWatch Logs${NC}"

echo -e "\n${RED}💰 This will STOP all charges for the project.${NC}"

read -p "Are you sure you want to proceed? (type 'yes' to confirm): " confirm
if [ "$confirm" != "yes" ]; then
    echo -e "${BLUE}✅ Cleanup cancelled.${NC}"
    exit 0
fi

# Check AWS CLI and credentials
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found.${NC}"
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured.${NC}"
    exit 1
fi

echo -e "\n${YELLOW}🏗️  Step 1: Scaling down ECS services...${NC}"

# Scale down services to 0 (faster deletion)
echo -e "${BLUE}⬇️  Scaling down API service...${NC}"
aws ecs update-service \
    --cluster ${PROJECT_NAME}-${ENVIRONMENT} \
    --service ${PROJECT_NAME}-${ENVIRONMENT}-api \
    --desired-count 0 \
    --region ${AWS_REGION} > /dev/null 2>&1 || echo "API service not found"

echo -e "${BLUE}⬇️  Scaling down Worker service...${NC}"
aws ecs update-service \
    --cluster ${PROJECT_NAME}-${ENVIRONMENT} \
    --service ${PROJECT_NAME}-${ENVIRONMENT}-worker \
    --desired-count 0 \
    --region ${AWS_REGION} > /dev/null 2>&1 || echo "Worker service not found"

# Wait for services to scale down
echo -e "${BLUE}⏳ Waiting for services to scale down...${NC}"
sleep 30

echo -e "\n${YELLOW}🗂️  Step 2: Deleting ECR images...${NC}"

# Get ECR repository names
ECR_API_REPO="${PROJECT_NAME}/${ENVIRONMENT}/api"
ECR_WORKER_REPO="${PROJECT_NAME}/${ENVIRONMENT}/worker"

# Delete all images in repositories
echo -e "${BLUE}🗑️  Deleting API images...${NC}"
aws ecr list-images \
    --repository-name ${ECR_API_REPO} \
    --region ${AWS_REGION} \
    --query 'imageIds[*]' \
    --output json > /tmp/api_images.json 2>/dev/null || echo "[]" > /tmp/api_images.json

if [ -s /tmp/api_images.json ] && [ "$(cat /tmp/api_images.json)" != "[]" ]; then
    aws ecr batch-delete-image \
        --repository-name ${ECR_API_REPO} \
        --image-ids file:///tmp/api_images.json \
        --region ${AWS_REGION} > /dev/null
fi

echo -e "${BLUE}🗑️  Deleting Worker images...${NC}"
aws ecr list-images \
    --repository-name ${ECR_WORKER_REPO} \
    --region ${AWS_REGION} \
    --query 'imageIds[*]' \
    --output json > /tmp/worker_images.json 2>/dev/null || echo "[]" > /tmp/worker_images.json

if [ -s /tmp/worker_images.json ] && [ "$(cat /tmp/worker_images.json)" != "[]" ]; then
    aws ecr batch-delete-image \
        --repository-name ${ECR_WORKER_REPO} \
        --image-ids file:///tmp/worker_images.json \
        --region ${AWS_REGION} > /dev/null
fi

echo -e "\n${YELLOW}📦 Step 3: Deleting Application Stack...${NC}"

aws cloudformation delete-stack \
    --stack-name ${PROJECT_NAME}-${ENVIRONMENT}-application \
    --region ${AWS_REGION}

echo -e "${BLUE}⏳ Waiting for application stack deletion...${NC}"
aws cloudformation wait stack-delete-complete \
    --stack-name ${PROJECT_NAME}-${ENVIRONMENT}-application \
    --region ${AWS_REGION}

echo -e "${GREEN}✅ Application stack deleted${NC}"

echo -e "\n${YELLOW}🏗️  Step 4: Deleting Infrastructure Stack...${NC}"

aws cloudformation delete-stack \
    --stack-name ${PROJECT_NAME}-${ENVIRONMENT}-infrastructure \
    --region ${AWS_REGION}

echo -e "${BLUE}⏳ Waiting for infrastructure stack deletion...${NC}"
aws cloudformation wait stack-delete-complete \
    --stack-name ${PROJECT_NAME}-${ENVIRONMENT}-infrastructure \
    --region ${AWS_REGION}

echo -e "${GREEN}✅ Infrastructure stack deleted${NC}"

echo -e "\n${YELLOW}📋 Step 5: Cleaning up CloudWatch Logs...${NC}"

# Delete log group
LOG_GROUP="/ecs/${PROJECT_NAME}-${ENVIRONMENT}"
aws logs delete-log-group \
    --log-group-name ${LOG_GROUP} \
    --region ${AWS_REGION} > /dev/null 2>&1 || echo "Log group not found"

echo -e "\n${GREEN}🎉 CLEANUP COMPLETE! 🎉${NC}"
echo -e "${GREEN}========================${NC}"
echo -e "${GREEN}✅ All AWS resources have been deleted${NC}"
echo -e "${GREEN}✅ No more charges will be incurred${NC}"
echo -e "\n${BLUE}📊 What was deleted:${NC}"
echo -e "${BLUE}  • ECS Cluster: ${PROJECT_NAME}-${ENVIRONMENT}${NC}"
echo -e "${BLUE}  • Load Balancer and Target Groups${NC}"
echo -e "${BLUE}  • VPC, Subnets, and Security Groups${NC}"
echo -e "${BLUE}  • ECR Repositories and Images${NC}"
echo -e "${BLUE}  • Redis Cluster${NC}"
echo -e "${BLUE}  • CloudWatch Log Groups${NC}"
echo -e "${BLUE}  • IAM Roles and Policies${NC}"

echo -e "\n${YELLOW}💡 Note: Your S3 bucket 'trod-video-clips' was NOT deleted.${NC}"
echo -e "${YELLOW}If you want to delete it too, run:${NC}"
echo -e "${YELLOW}  aws s3 rm s3://trod-video-clips --recursive${NC}"
echo -e "${YELLOW}  aws s3 rb s3://trod-video-clips${NC}"

# Cleanup temp files
rm -f /tmp/api_images.json /tmp/worker_images.json 