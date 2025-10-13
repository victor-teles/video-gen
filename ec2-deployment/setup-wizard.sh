#!/bin/bash

# Editur AI Backend - Complete Setup Wizard
# This script guides you through the entire AWS setup and deployment process

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_step() { echo -e "${PURPLE}[STEP]${NC} $1"; }

clear
echo ""
echo "🚀 EDITUR AI BACKEND DEPLOYMENT WIZARD"
echo "======================================"
echo ""
echo "Account: azeemushanofficial@gmail.com"
echo "Target: AWS EC2 Spot Instance (~\$10-15/month)"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI not found!"
    echo ""
    echo "It seems AWS CLI installation didn't complete properly."
    echo "Please restart your terminal and try again."
    echo ""
    echo "If the issue persists, manually install from:"
    echo "https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

log_success "AWS CLI is installed: $(aws --version)"
echo ""

# Step 1: Check AWS Configuration
log_step "STEP 1: Checking AWS Configuration"
echo ""

if aws sts get-caller-identity &> /dev/null; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    USER_ARN=$(aws sts get-caller-identity --query Arn --output text)
    REGION=$(aws configure get region)
    
    log_success "AWS credentials are configured"
    echo "   Account ID: $ACCOUNT_ID"
    echo "   User: $USER_ARN"
    echo "   Region: ${REGION:-'Not set'}"
    
    echo ""
    echo "✅ You're already set up! Proceeding to validation..."
    
else
    log_warning "AWS credentials not configured"
    echo ""
    echo "🎯 You need to complete AWS Console setup first:"
    echo ""
    echo "1. 📖 READ the setup guide: ./ec2-deployment/AWS_CONSOLE_SETUP.md"
    echo "2. 🌐 Complete AWS Console configuration"
    echo "3. 🔑 Get your Access Keys from IAM"
    echo "4. 🔧 Run: aws configure"
    echo "5. 🔄 Run this script again"
    echo ""
    
    read -p "❓ Have you completed the AWS Console setup? (y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Let's configure AWS CLI now..."
        echo ""
        echo "📋 You'll need your:"
        echo "   - AWS Access Key ID"
        echo "   - AWS Secret Access Key"
        echo "   - Default region (recommend: us-east-1)"
        echo ""
        
        aws configure
        
        echo ""
        log_info "Testing credentials..."
        if aws sts get-caller-identity &> /dev/null; then
            log_success "Credentials configured successfully!"
        else
            log_error "Credential test failed. Please check your keys and try again."
            exit 1
        fi
        
    else
        echo ""
        log_info "📚 Next steps:"
        echo "1. Open: ./ec2-deployment/AWS_CONSOLE_SETUP.md"
        echo "2. Complete ALL steps in the AWS Console"
        echo "3. Run this script again when done"
        echo ""
        exit 0
    fi
fi

echo ""

# Step 2: Validate Setup
log_step "STEP 2: Validating AWS Setup"
echo ""

log_info "Running comprehensive validation..."
./ec2-deployment/validate-aws-setup.sh

echo ""

# Step 3: API Keys Setup
log_step "STEP 3: API Keys Configuration"
echo ""

log_info "For full functionality, you'll need these API keys:"
echo ""
echo "🔑 Required for Faceless Video Generation:"
echo "   - OpenAI API Key (for GPT-4 and Text-to-Speech)"
echo "   - Replicate API Token (for AI image generation)"
echo ""
echo "💡 You can deploy without these keys and add them later."
echo ""

read -p "❓ Do you have your API keys ready? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    read -p "🔑 Enter your OpenAI API Key (or press Enter to skip): " OPENAI_KEY
    read -p "🔑 Enter your Replicate API Token (or press Enter to skip): " REPLICATE_KEY
    
    # Save to temporary file for later use
    cat > /tmp/editur-api-keys.env << EOF
OPENAI_API_KEY=${OPENAI_KEY}
REPLICATE_API_TOKEN=${REPLICATE_KEY}
EOF
    
    if [[ -n "$OPENAI_KEY" ]] || [[ -n "$REPLICATE_KEY" ]]; then
        log_success "API keys saved temporarily (will be configured after deployment)"
    fi
else
    log_info "Proceeding without API keys (you can add them later)"
fi

echo ""

# Step 4: Pre-deployment Check
log_step "STEP 4: Pre-deployment Verification"
echo ""

log_info "Final checks before deployment..."

# Check if deployment script exists
if [[ ! -f "./ec2-deployment/deploy-ec2-spot.sh" ]]; then
    log_error "Deployment script not found!"
    echo "Please ensure you're in the correct directory with deployment scripts."
    exit 1
fi

# Verify permissions
aws sts get-caller-identity > /dev/null

log_success "All checks passed!"
echo ""

# Step 5: Deploy
log_step "STEP 5: Deploy to AWS EC2 Spot"
echo ""

echo "🚀 Ready to deploy Editur AI Backend!"
echo ""
echo "📊 What will be created:"
echo "   - EC2 t3.medium Spot Instance (~\$7-10/month)"
echo "   - Security Groups for web access"
echo "   - S3 bucket for video storage (~\$1-2/month)"
echo "   - Complete backend setup with monitoring"
echo ""
echo "⏱️  Deployment time: 5-10 minutes"
echo "💰 Estimated monthly cost: \$10-15"
echo ""

read -p "🎯 Proceed with deployment? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    log_success "🚀 Starting deployment..."
    echo ""
    
    # Run deployment
    ./ec2-deployment/deploy-ec2-spot.sh
    
    # If deployment succeeds, configure API keys
    if [[ $? -eq 0 ]] && [[ -f "/tmp/editur-api-keys.env" ]]; then
        echo ""
        log_info "🔑 Configuring API keys on server..."
        
        # Get instance info
        if [[ -f "deployment-info.json" ]]; then
            PUBLIC_IP=$(grep -o '"public_ip": "[^"]*' deployment-info.json | cut -d'"' -f4)
            KEY_NAME=$(grep -o '"key_name": "[^"]*' deployment-info.json | cut -d'"' -f4)
            
            if [[ -n "$PUBLIC_IP" ]] && [[ -n "$KEY_NAME" ]] && [[ -f "${KEY_NAME}.pem" ]]; then
                log_info "Waiting for server to be ready..."
                sleep 30
                
                # Copy API keys to server
                scp -i "${KEY_NAME}.pem" -o StrictHostKeyChecking=no /tmp/editur-api-keys.env ubuntu@${PUBLIC_IP}:/tmp/
                
                # Update .env file on server
                ssh -i "${KEY_NAME}.pem" -o StrictHostKeyChecking=no ubuntu@${PUBLIC_IP} '
                    sudo bash -c "
                        source /tmp/editur-api-keys.env
                        if [[ -n \"\$OPENAI_API_KEY\" ]]; then
                            sed -i \"s/OPENAI_API_KEY=.*/OPENAI_API_KEY=\$OPENAI_API_KEY/\" /opt/editur-ai/backend/.env
                        fi
                        if [[ -n \"\$REPLICATE_API_TOKEN\" ]]; then
                            sed -i \"s/REPLICATE_API_TOKEN=.*/REPLICATE_API_TOKEN=\$REPLICATE_API_TOKEN/\" /opt/editur-ai/backend/.env
                        fi
                        systemctl restart editur-api editur-worker
                    "
                    rm /tmp/editur-api-keys.env
                '
                
                log_success "API keys configured successfully!"
            fi
        fi
        
        # Clean up
        rm -f /tmp/editur-api-keys.env
    fi
    
    echo ""
    log_success "🎉 Deployment wizard completed!"
    
    if [[ -f "deployment-info.json" ]]; then
        PUBLIC_IP=$(grep -o '"public_ip": "[^"]*' deployment-info.json | cut -d'"' -f4)
        
        echo ""
        echo "🌐 Your Editur AI Backend is live at:"
        echo "   API: http://$PUBLIC_IP/"
        echo "   Docs: http://$PUBLIC_IP/docs"
        echo "   Health: http://$PUBLIC_IP/health"
        echo ""
        echo "💡 Next Steps:"
        echo "   1. Test your API endpoints"
        echo "   2. Connect your frontend to http://$PUBLIC_IP/"
        echo "   3. Monitor costs in AWS Console"
        echo ""
        echo "🔧 Management:"
        echo "   - SSH: ssh -i *.pem ubuntu@$PUBLIC_IP"
        echo "   - Logs: ssh -i *.pem ubuntu@$PUBLIC_IP 'sudo journalctl -u editur-api -f'"
        echo "   - Stop: aws ec2 stop-instances --instance-ids \$(grep instance_id deployment-info.json | cut -d'\"' -f4)"
        echo ""
    fi
    
else
    log_info "Deployment cancelled. You can run this script again anytime."
fi

echo ""
echo "📚 Additional Resources:"
echo "   - Full deployment guide: ./ec2-deployment/DEPLOYMENT_GUIDE.md"
echo "   - AWS Console setup: ./ec2-deployment/AWS_CONSOLE_SETUP.md"
echo "   - Validate setup: ./ec2-deployment/validate-aws-setup.sh"
echo ""

log_success "Wizard completed!"