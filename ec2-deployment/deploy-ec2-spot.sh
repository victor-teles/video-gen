#!/bin/bash

# AWS EC2 Spot Instance Deployment Script for Editur AI Backend
# This script launches a cost-optimized EC2 spot instance and deploys the backend

set -e

# Configuration
PROJECT_NAME="editur-ai"
INSTANCE_TYPE="t3.medium"  # 2 vCPU, 4GB RAM - good balance for video processing
SPOT_PRICE="0.0416"        # Max price (70% of on-demand)
AMI_ID="ami-0c7217cdde317cfec"  # Ubuntu 22.04 LTS (us-east-1)
KEY_NAME=""                # Will be prompted
REGION="us-east-1"
AVAILABILITY_ZONE="us-east-1a"

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
    log_error "AWS CLI is not installed. Please install it first:"
    echo "https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured. Run: aws configure"
    exit 1
fi

log_info "AWS Account: $(aws sts get-caller-identity --query Account --output text)"
log_info "Region: $REGION"

# Get or create key pair
if [ -z "$KEY_NAME" ]; then
    echo ""
    echo "Available key pairs:"
    aws ec2 describe-key-pairs --query 'KeyPairs[].KeyName' --output table --region $REGION
    echo ""
    read -p "Enter existing key pair name (or press Enter to create new): " KEY_NAME
    
    if [ -z "$KEY_NAME" ]; then
        KEY_NAME="editur-ai-$(date +%Y%m%d)"
        log_info "Creating new key pair: $KEY_NAME"
        aws ec2 create-key-pair \
            --key-name $KEY_NAME \
            --query 'KeyMaterial' \
            --output text \
            --region $REGION > ${KEY_NAME}.pem
        chmod 400 ${KEY_NAME}.pem
        log_success "Key pair created and saved as ${KEY_NAME}.pem"
    fi
fi

# Create security group
SECURITY_GROUP_NAME="${PROJECT_NAME}-sg"
log_info "Creating security group: $SECURITY_GROUP_NAME"

# Check if security group exists
SG_ID=$(aws ec2 describe-security-groups \
    --group-names $SECURITY_GROUP_NAME \
    --query 'SecurityGroups[0].GroupId' \
    --output text \
    --region $REGION 2>/dev/null || echo "None")

if [ "$SG_ID" = "None" ]; then
    # Create new security group
    SG_ID=$(aws ec2 create-security-group \
        --group-name $SECURITY_GROUP_NAME \
        --description "Security group for Editur AI Backend" \
        --query 'GroupId' \
        --output text \
        --region $REGION)
    
    log_success "Created security group: $SG_ID"
    
    # Add rules
    log_info "Adding security group rules..."
    
    # SSH access (restrict to your IP)
    MY_IP=$(curl -s https://checkip.amazonaws.com)/32
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 22 \
        --cidr $MY_IP \
        --region $REGION
    
    # HTTP access
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    
    # HTTPS access
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    
    log_success "Security group rules added"
else
    log_info "Using existing security group: $SG_ID"
fi

# Create user data script (base64 encoded)
USER_DATA=$(cat << 'EOF' | base64 -w 0
#!/bin/bash
# Initial setup script run on instance launch
apt-get update -y
apt-get install -y curl git

# Create setup log
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "Starting Editur AI Backend setup..."
echo "Time: $(date)"

# Download and run the main setup script
cd /tmp
curl -L https://raw.githubusercontent.com/ZetaSoftdev/video_clip_generator/main/ec2-deployment/setup-server.sh -o setup-server.sh
chmod +x setup-server.sh

# Run as ubuntu user
su - ubuntu -c "cd /tmp && ./setup-server.sh"

echo "User data script completed at $(date)"
EOF
)

# Request spot instance
log_info "Requesting spot instance (max price: $${SPOT_PRICE}/hour)..."

SPOT_REQUEST_ID=$(aws ec2 request-spot-instances \
    --spot-price $SPOT_PRICE \
    --instance-count 1 \
    --type "persistent" \
    --launch-specification "{
        \"ImageId\": \"$AMI_ID\",
        \"InstanceType\": \"$INSTANCE_TYPE\",
        \"KeyName\": \"$KEY_NAME\",
        \"SecurityGroupIds\": [\"$SG_ID\"],
        \"Placement\": {
            \"AvailabilityZone\": \"$AVAILABILITY_ZONE\"
        },
        \"UserData\": \"$USER_DATA\",
        \"BlockDeviceMappings\": [{
            \"DeviceName\": \"/dev/sda1\",
            \"Ebs\": {
                \"VolumeSize\": 20,
                \"VolumeType\": \"gp3\",
                \"DeleteOnTermination\": true
            }
        }]
    }" \
    --query 'SpotInstanceRequests[0].SpotInstanceRequestId' \
    --output text \
    --region $REGION)

if [ "$SPOT_REQUEST_ID" = "None" ] || [ -z "$SPOT_REQUEST_ID" ]; then
    log_error "Failed to request spot instance"
    exit 1
fi

log_success "Spot instance requested: $SPOT_REQUEST_ID"

# Wait for spot request to be fulfilled
log_info "Waiting for spot instance to be fulfilled..."
aws ec2 wait spot-instance-request-fulfilled \
    --spot-instance-request-ids $SPOT_REQUEST_ID \
    --region $REGION

# Get instance ID
INSTANCE_ID=$(aws ec2 describe-spot-instance-requests \
    --spot-instance-request-ids $SPOT_REQUEST_ID \
    --query 'SpotInstanceRequests[0].InstanceId' \
    --output text \
    --region $REGION)

log_success "Spot instance launched: $INSTANCE_ID"

# Wait for instance to be running
log_info "Waiting for instance to be running..."
aws ec2 wait instance-running \
    --instance-ids $INSTANCE_ID \
    --region $REGION

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text \
    --region $REGION)

log_success "Instance is running!"
echo ""
echo "🎉 Editur AI Backend Deployment Started!"
echo ""
echo "📋 Instance Details:"
echo "   Instance ID: $INSTANCE_ID"
echo "   Public IP: $PUBLIC_IP"
echo "   Instance Type: $INSTANCE_TYPE"
echo "   Spot Price: \$$SPOT_PRICE/hour"
echo "   Key Pair: $KEY_NAME"
echo ""
echo "⏳ Setup in Progress (5-10 minutes)..."
echo "   The server is automatically installing all dependencies"
echo ""
echo "🔗 Access URLs (available after setup completes):"
echo "   🌐 API: http://$PUBLIC_IP/"
echo "   📚 Docs: http://$PUBLIC_IP/docs"
echo "   ❤️  Health: http://$PUBLIC_IP/health"
echo ""
echo "💻 SSH Access:"
echo "   ssh -i ${KEY_NAME}.pem ubuntu@$PUBLIC_IP"
echo ""
echo "📊 Monitor Setup Progress:"
echo "   ssh -i ${KEY_NAME}.pem ubuntu@$PUBLIC_IP 'tail -f /var/log/user-data.log'"
echo ""
echo "🔧 Manual Commands:"
echo "   # Check status"
echo "   ssh -i ${KEY_NAME}.pem ubuntu@$PUBLIC_IP '/opt/editur-ai/monitor.sh'"
echo ""
echo "   # View logs"
echo "   ssh -i ${KEY_NAME}.pem ubuntu@$PUBLIC_IP 'sudo journalctl -u editur-api -f'"
echo ""
echo "   # Restart services"
echo "   ssh -i ${KEY_NAME}.pem ubuntu@$PUBLIC_IP 'sudo systemctl restart editur-api editur-worker'"
echo ""
echo "💰 Cost Optimization:"
echo "   - Monthly cost: ~\$10-15 (with spot pricing)"
echo "   - Stop when not in use: aws ec2 stop-instances --instance-ids $INSTANCE_ID"
echo "   - Terminate: aws ec2 terminate-instances --instance-ids $INSTANCE_ID"
echo ""
echo "⚠️  Important Notes:"
echo "   1. Edit /opt/editur-ai/backend/.env with your API keys after setup"
echo "   2. Spot instances can be interrupted (with 2-minute notice)"
echo "   3. Use Elastic IP if you need a static IP address"
echo ""

# Save deployment info
cat > deployment-info.json << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "instance_id": "$INSTANCE_ID",
  "public_ip": "$PUBLIC_IP",
  "spot_request_id": "$SPOT_REQUEST_ID",
  "key_name": "$KEY_NAME",
  "security_group_id": "$SG_ID",
  "region": "$REGION",
  "instance_type": "$INSTANCE_TYPE",
  "spot_price": "$SPOT_PRICE",
  "ssh_command": "ssh -i ${KEY_NAME}.pem ubuntu@$PUBLIC_IP",
  "api_url": "http://$PUBLIC_IP/",
  "docs_url": "http://$PUBLIC_IP/docs",
  "health_url": "http://$PUBLIC_IP/health"
}
EOF

log_success "Deployment info saved to deployment-info.json"

# Wait and test
log_info "Waiting 5 minutes for setup to complete, then testing..."
echo "You can monitor progress with:"
echo "ssh -i ${KEY_NAME}.pem ubuntu@$PUBLIC_IP 'tail -f /var/log/user-data.log'"
echo ""

sleep 300  # Wait 5 minutes

# Test if API is responding
if curl -s http://$PUBLIC_IP/health > /dev/null; then
    log_success "🎉 API is responding! Deployment successful!"
    echo "🌐 Your Editur AI Backend is live at: http://$PUBLIC_IP/"
else
    log_warning "API not responding yet. Setup may still be in progress."
    echo "Check setup progress: ssh -i ${KEY_NAME}.pem ubuntu@$PUBLIC_IP 'tail -f /var/log/user-data.log'"
fi

echo ""
log_success "Deployment script completed!"