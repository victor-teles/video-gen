#!/bin/bash

# AWS Setup Validation Script for Editur AI
# This script validates your AWS setup before deployment

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

echo "🔍 AWS Setup Validation for Editur AI Backend"
echo "=============================================="
echo ""

# Check 1: AWS CLI Installation
log_info "Checking AWS CLI installation..."
if command -v aws &> /dev/null; then
    AWS_VERSION=$(aws --version)
    log_success "AWS CLI installed: $AWS_VERSION"
else
    log_error "AWS CLI is not installed or not in PATH"
    echo "Please install AWS CLI first"
    exit 1
fi

# Check 2: AWS Credentials
log_info "Checking AWS credentials..."
if aws sts get-caller-identity &> /dev/null; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    USER_ARN=$(aws sts get-caller-identity --query Arn --output text)
    REGION=$(aws configure get region)
    
    log_success "AWS credentials configured"
    echo "   Account ID: $ACCOUNT_ID"
    echo "   User/Role: $USER_ARN"
    echo "   Region: ${REGION:-'Not set'}"
    
    # Warn if using root credentials
    if [[ $USER_ARN == *":root" ]]; then
        log_warning "You're using root credentials. Consider creating IAM user for security."
    fi
    
    # Check if region is set
    if [[ -z "$REGION" ]]; then
        log_warning "Default region not set. Setting to us-east-1..."
        aws configure set region us-east-1
        REGION="us-east-1"
    fi
    
else
    log_error "AWS credentials not configured or invalid"
    echo "Run: aws configure"
    exit 1
fi

echo ""

# Check 3: Required Permissions
log_info "Checking IAM permissions..."

# Test EC2 permissions
if aws ec2 describe-regions --region $REGION &> /dev/null; then
    log_success "EC2 permissions: OK"
else
    log_error "EC2 permissions: MISSING"
    echo "Required: AmazonEC2FullAccess or equivalent"
fi

# Test S3 permissions
if aws s3 ls &> /dev/null; then
    log_success "S3 permissions: OK"
else
    log_error "S3 permissions: MISSING"
    echo "Required: AmazonS3FullAccess or equivalent"
fi

# Test IAM permissions (for creating security groups, etc.)
if aws iam get-user &> /dev/null 2>&1 || aws sts get-caller-identity &> /dev/null; then
    log_success "IAM permissions: OK"
else
    log_warning "IAM permissions: LIMITED (may affect advanced features)"
fi

echo ""

# Check 4: Key Pairs
log_info "Checking EC2 Key Pairs..."
KEY_PAIRS=$(aws ec2 describe-key-pairs --region $REGION --query 'KeyPairs[].KeyName' --output text 2>/dev/null || echo "")

if [[ -n "$KEY_PAIRS" ]]; then
    log_success "Key pairs found: $KEY_PAIRS"
else
    log_warning "No key pairs found. You'll need to create one for EC2 access."
    echo "To create: AWS Console → EC2 → Key Pairs → Create key pair"
fi

echo ""

# Check 5: VPC and Subnets
log_info "Checking VPC configuration..."
DEFAULT_VPC=$(aws ec2 describe-vpcs --region $REGION --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text 2>/dev/null || echo "None")

if [[ "$DEFAULT_VPC" != "None" ]] && [[ "$DEFAULT_VPC" != "null" ]]; then
    log_success "Default VPC available: $DEFAULT_VPC"
    
    # Check subnets
    SUBNETS=$(aws ec2 describe-subnets --region $REGION --filters "Name=vpc-id,Values=$DEFAULT_VPC" --query 'length(Subnets)' --output text 2>/dev/null || echo "0")
    if [[ "$SUBNETS" -gt 0 ]]; then
        log_success "Subnets available: $SUBNETS"
    else
        log_warning "No subnets found in default VPC"
    fi
else
    log_warning "No default VPC found. Deployment will create one."
fi

echo ""

# Check 6: Free Tier Status
log_info "Checking account status..."

# Try to get account attributes
ACCOUNT_ATTRS=$(aws ec2 describe-account-attributes --region $REGION 2>/dev/null || echo "")
if [[ -n "$ACCOUNT_ATTRS" ]]; then
    log_success "Account is active and accessible"
else
    log_warning "Account status unclear - may need verification"
fi

echo ""

# Check 7: Spot Instance Availability
log_info "Checking Spot Instance availability..."
SPOT_PRICE=$(aws ec2 describe-spot-price-history \
    --instance-types t3.medium \
    --product-descriptions "Linux/UNIX" \
    --region $REGION \
    --max-items 1 \
    --query 'SpotPriceHistory[0].SpotPrice' \
    --output text 2>/dev/null || echo "Unknown")

if [[ "$SPOT_PRICE" != "Unknown" ]] && [[ "$SPOT_PRICE" != "null" ]]; then
    log_success "Spot instances available. Current t3.medium price: \$$SPOT_PRICE/hour"
    MONTHLY_COST=$(echo "$SPOT_PRICE * 24 * 30" | bc 2>/dev/null || echo "~10-15")
    echo "   Estimated monthly cost: \$${MONTHLY_COST}"
else
    log_warning "Could not retrieve spot pricing. Spot instances may still be available."
fi

echo ""

# Check 8: Service Limits
log_info "Checking service limits..."
EC2_LIMIT=$(aws service-quotas get-service-quota \
    --service-code ec2 \
    --quota-code L-1216C47A \
    --region $REGION \
    --query 'Quota.Value' \
    --output text 2>/dev/null || echo "Unknown")

if [[ "$EC2_LIMIT" != "Unknown" ]] && [[ "$EC2_LIMIT" != "null" ]]; then
    log_success "EC2 instance limit: $EC2_LIMIT"
    if (( $(echo "$EC2_LIMIT >= 1" | bc -l) )); then
        log_success "Sufficient limit for deployment"
    else
        log_warning "Low instance limit. May need to request increase."
    fi
else
    log_info "Could not check EC2 limits (common for new accounts)"
fi

echo ""

# Summary and Recommendations
echo "📋 SETUP VALIDATION SUMMARY"
echo "=========================="

ISSUES=0

if ! command -v aws &> /dev/null; then
    log_error "AWS CLI not installed"
    ((ISSUES++))
fi

if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured"
    ((ISSUES++))
fi

if ! aws ec2 describe-regions --region $REGION &> /dev/null; then
    log_error "Missing EC2 permissions"
    ((ISSUES++))
fi

if ! aws s3 ls &> /dev/null; then
    log_error "Missing S3 permissions"
    ((ISSUES++))
fi

if [[ -z "$KEY_PAIRS" ]]; then
    log_warning "No SSH key pairs (you can create during deployment)"
fi

echo ""

if [[ $ISSUES -eq 0 ]]; then
    log_success "🎉 All critical checks passed! Ready for deployment."
    echo ""
    echo "💡 Next Steps:"
    echo "   1. Run: ./ec2-deployment/deploy-ec2-spot.sh"
    echo "   2. Follow the deployment script prompts"
    echo "   3. Configure your environment variables after deployment"
    echo ""
    echo "💰 Estimated Costs:"
    echo "   - EC2 Spot (t3.medium): ~\$10/month"
    echo "   - S3 Storage: ~\$1-2/month"
    echo "   - Data Transfer: ~\$2-3/month"
    echo "   - Total: ~\$13-15/month"
    echo ""
    echo "🔗 Useful Commands:"
    echo "   - Check costs: aws ce get-cost-and-usage --time-period Start=\$(date -d '1 month ago' +%Y-%m-%d),End=\$(date +%Y-%m-%d) --granularity MONTHLY --metrics BlendedCost"
    echo "   - List instances: aws ec2 describe-instances --region $REGION"
    echo "   - Stop instance: aws ec2 stop-instances --instance-ids i-xxxxx"
else
    log_error "❌ Found $ISSUES critical issues. Please resolve before deployment."
    echo ""
    echo "🔧 Common Solutions:"
    echo "   - Missing permissions: Add policies in IAM Console"
    echo "   - Invalid credentials: Run 'aws configure' with correct keys"
    echo "   - No key pairs: Create in EC2 Console → Key Pairs"
fi

echo ""
echo "📚 Need Help?"
echo "   - Setup Guide: ./ec2-deployment/AWS_CONSOLE_SETUP.md"
echo "   - Deployment Guide: ./ec2-deployment/DEPLOYMENT_GUIDE.md"
echo "   - AWS Console: https://console.aws.amazon.com"