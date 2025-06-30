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

echo -e "${BLUE}🚀 Video Clip Generator - AWS Deployment Script${NC}"
echo -e "${BLUE}=================================================${NC}"

# Check prerequisites
echo -e "\n${YELLOW}📋 Checking prerequisites...${NC}"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install AWS CLI first.${NC}"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured. Please run 'aws configure' first.${NC}"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites satisfied${NC}"

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${BLUE}🔍 AWS Account ID: ${AWS_ACCOUNT_ID}${NC}"

# Step 1: Deploy Infrastructure
echo -e "\n${YELLOW}🏗️  Step 1: Deploying Infrastructure...${NC}"

aws cloudformation deploy \
    --template-file cloudformation-infrastructure.yml \
    --stack-name ${PROJECT_NAME}-${ENVIRONMENT}-infrastructure \
    --parameter-overrides \
        ProjectName=${PROJECT_NAME} \
        Environment=${ENVIRONMENT} \
    --capabilities CAPABILITY_IAM \
    --region ${AWS_REGION} \
    --no-fail-on-empty-changeset

echo -e "${GREEN}✅ Infrastructure deployed successfully${NC}"

# Step 2: Deploy Application Resources
echo -e "\n${YELLOW}📦 Step 2: Deploying Application Resources...${NC}"

aws cloudformation deploy \
    --template-file cloudformation-application.yml \
    --stack-name ${PROJECT_NAME}-${ENVIRONMENT}-application \
    --parameter-overrides \
        ProjectName=${PROJECT_NAME} \
        Environment=${ENVIRONMENT} \
        ImageTag=latest \
    --capabilities CAPABILITY_IAM \
    --region ${AWS_REGION} \
    --no-fail-on-empty-changeset

echo -e "${GREEN}✅ Application resources deployed successfully${NC}"

# Step 3: Get ECR Repository URIs
echo -e "\n${YELLOW}🔍 Step 3: Getting ECR Repository URIs...${NC}"

ECR_API_URI=$(aws cloudformation describe-stacks \
    --stack-name ${PROJECT_NAME}-${ENVIRONMENT}-application \
    --query 'Stacks[0].Outputs[?OutputKey==`ECRRepositoryAPIURI`].OutputValue' \
    --output text \
    --region ${AWS_REGION})

ECR_WORKER_URI=$(aws cloudformation describe-stacks \
    --stack-name ${PROJECT_NAME}-${ENVIRONMENT}-application \
    --query 'Stacks[0].Outputs[?OutputKey==`ECRRepositoryWorkerURI`].OutputValue' \
    --output text \
    --region ${AWS_REGION})

echo -e "${BLUE}📦 API ECR URI: ${ECR_API_URI}${NC}"
echo -e "${BLUE}📦 Worker ECR URI: ${ECR_WORKER_URI}${NC}"

# Step 4: Login to ECR
echo -e "\n${YELLOW}🔐 Step 4: Logging into ECR...${NC}"

aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

echo -e "${GREEN}✅ ECR login successful${NC}"

# Step 5: Build and Push Docker Images
echo -e "\n${YELLOW}🐳 Step 5: Building and Pushing Docker Images...${NC}"

# Navigate to project root (assuming script is in deployment/ folder)
cd ..

# Build and push API image
echo -e "${BLUE}🔨 Building API image...${NC}"
docker build -f Dockerfile -t ${ECR_API_URI}:latest .
docker tag ${ECR_API_URI}:latest ${ECR_API_URI}:$(date +%Y%m%d%H%M%S)

echo -e "${BLUE}📤 Pushing API image...${NC}"
docker push ${ECR_API_URI}:latest
docker push ${ECR_API_URI}:$(date +%Y%m%d%H%M%S)

# Build and push Worker image
echo -e "${BLUE}🔨 Building Worker image...${NC}"
docker build -f Dockerfile.worker -t ${ECR_WORKER_URI}:latest .
docker tag ${ECR_WORKER_URI}:latest ${ECR_WORKER_URI}:$(date +%Y%m%d%H%M%S)

echo -e "${BLUE}📤 Pushing Worker image...${NC}"
docker push ${ECR_WORKER_URI}:latest
docker push ${ECR_WORKER_URI}:$(date +%Y%m%d%H%M%S)

echo -e "${GREEN}✅ All images built and pushed successfully${NC}"

# Step 6: Update ECS Services
echo -e "\n${YELLOW}🚀 Step 6: Updating ECS Services...${NC}"

# Update API service
echo -e "${BLUE}🔄 Updating API service...${NC}"
aws ecs update-service \
    --cluster ${PROJECT_NAME}-${ENVIRONMENT} \
    --service ${PROJECT_NAME}-${ENVIRONMENT}-api \
    --force-new-deployment \
    --region ${AWS_REGION} > /dev/null

# Update Worker service
echo -e "${BLUE}🔄 Updating Worker service...${NC}"
aws ecs update-service \
    --cluster ${PROJECT_NAME}-${ENVIRONMENT} \
    --service ${PROJECT_NAME}-${ENVIRONMENT}-worker \
    --force-new-deployment \
    --region ${AWS_REGION} > /dev/null

echo -e "${GREEN}✅ Services updated successfully${NC}"

# Step 7: Wait for deployment to complete
echo -e "\n${YELLOW}⏳ Step 7: Waiting for deployment to complete...${NC}"

echo -e "${BLUE}⏳ Waiting for API service to stabilize...${NC}"
aws ecs wait services-stable \
    --cluster ${PROJECT_NAME}-${ENVIRONMENT} \
    --services ${PROJECT_NAME}-${ENVIRONMENT}-api \
    --region ${AWS_REGION}

echo -e "${BLUE}⏳ Waiting for Worker service to stabilize...${NC}"
aws ecs wait services-stable \
    --cluster ${PROJECT_NAME}-${ENVIRONMENT} \
    --services ${PROJECT_NAME}-${ENVIRONMENT}-worker \
    --region ${AWS_REGION}

echo -e "${GREEN}✅ All services are stable${NC}"

# Step 8: Get Load Balancer URL and Test
echo -e "\n${YELLOW}🧪 Step 8: Testing Deployment...${NC}"

LOAD_BALANCER_URL=$(aws cloudformation describe-stacks \
    --stack-name ${PROJECT_NAME}-${ENVIRONMENT}-infrastructure \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerUrl`].OutputValue' \
    --output text \
    --region ${AWS_REGION})

echo -e "${BLUE}🌐 Load Balancer URL: ${LOAD_BALANCER_URL}${NC}"

# Wait a bit for load balancer to route traffic
echo -e "${BLUE}⏳ Waiting for load balancer to route traffic...${NC}"
sleep 30

# Test health endpoint
echo -e "${BLUE}🏥 Testing health endpoint...${NC}"
if curl -f "${LOAD_BALANCER_URL}/api/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
    exit 1
fi

# Test main endpoint
echo -e "${BLUE}🏠 Testing main endpoint...${NC}"
if curl -f "${LOAD_BALANCER_URL}/" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Main endpoint accessible${NC}"
else
    echo -e "${RED}❌ Main endpoint failed${NC}"
    exit 1
fi

# Final success message
echo -e "\n${GREEN}🎉 DEPLOYMENT SUCCESSFUL! 🎉${NC}"
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}🌐 Application URL: ${LOAD_BALANCER_URL}${NC}"
echo -e "${GREEN}📖 API Documentation: ${LOAD_BALANCER_URL}/docs${NC}"
echo -e "${GREEN}🏥 Health Check: ${LOAD_BALANCER_URL}/api/health${NC}"
echo -e "\n${BLUE}📋 Management Commands:${NC}"
echo -e "${BLUE}  • View logs: aws logs tail /ecs/${PROJECT_NAME}-${ENVIRONMENT} --follow${NC}"
echo -e "${BLUE}  • Scale API: aws ecs update-service --cluster ${PROJECT_NAME}-${ENVIRONMENT} --service ${PROJECT_NAME}-${ENVIRONMENT}-api --desired-count 2${NC}"
echo -e "${BLUE}  • Scale Worker: aws ecs update-service --cluster ${PROJECT_NAME}-${ENVIRONMENT} --service ${PROJECT_NAME}-${ENVIRONMENT}-worker --desired-count 2${NC}"

echo -e "\n${YELLOW}💰 Estimated Monthly Cost: \$75-100 (5-10 videos/day)${NC}"
echo -e "${YELLOW}🔧 To add custom domain, update the CloudFormation template with ACM certificate${NC}" 