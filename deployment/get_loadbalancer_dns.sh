#!/bin/bash

# Get Load Balancer DNS Name for Domain Configuration
# This script retrieves the AWS Load Balancer DNS name that you need to point your domain to

echo "🔍 Getting Load Balancer DNS name for api.trod.ai configuration..."
echo ""

# Check if AWS CLI is configured
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install AWS CLI first."
    exit 1
fi

# Get the load balancer DNS name from CloudFormation
STACK_NAME="video-clip-generator-production-infrastructure"
DNS_NAME=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNSName`].OutputValue' \
    --output text 2>/dev/null)

if [ -z "$DNS_NAME" ] || [ "$DNS_NAME" == "None" ]; then
    echo "❌ Could not retrieve Load Balancer DNS name."
    echo "   Make sure the infrastructure stack is deployed successfully."
    echo ""
    echo "🔧 Troubleshooting:"
    echo "   1. Check if the stack exists:"
    echo "      aws cloudformation describe-stacks --stack-name $STACK_NAME"
    echo ""
    echo "   2. Check deployment status:"
    echo "      aws cloudformation describe-stack-events --stack-name $STACK_NAME"
    exit 1
fi

echo "✅ Load Balancer DNS Name: $DNS_NAME"
echo ""
echo "📋 Next Steps for Domain Configuration:"
echo ""
echo "1. 🌐 Configure DNS Records:"
echo "   In your domain management panel for trod.ai, create:"
echo ""
echo "   Option A - CNAME Record (Recommended):"
echo "   Type: CNAME"
echo "   Name: api"
echo "   Value: $DNS_NAME"
echo "   TTL: 300"
echo ""
echo "   Option B - A Record (Alternative):"
echo "   Type: A"
echo "   Name: api"
echo "   Value: [Get IP of $DNS_NAME]"
echo "   TTL: 300"
echo ""
echo "2. 🔒 Configure SSL:"
echo "   - Ensure your SSL certificate covers api.trod.ai"
echo "   - Point SSL origin to: $DNS_NAME"
echo "   - Set SSL mode to 'Full' or 'Full (Strict)'"
echo ""
echo "3. 🧪 Test Configuration (after DNS propagation ~5-15 minutes):"
echo "   curl https://api.trod.ai/api/health"
echo "   curl https://api.trod.ai/docs"
echo ""
echo "4. 📖 For detailed instructions, see: deployment/DOMAIN_SETUP.md"
echo ""

# Also get the regular load balancer URL for reference
LB_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerUrl`].OutputValue' \
    --output text 2>/dev/null)

if [ ! -z "$LB_URL" ] && [ "$LB_URL" != "None" ]; then
    echo "📝 Current Load Balancer URL (for testing): $LB_URL"
    echo ""
fi

echo "🎯 Your API will be available at: https://api.trod.ai" 