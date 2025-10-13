#!/bin/bash

# Quick deploy script that automates the deployment with our existing setup
# This uses the credentials and key pair we've already created

set -e

PROJECT_NAME="editur-ai"
INSTANCE_TYPE="t3.medium"
SPOT_PRICE="0.0416" 
AMI_ID="ami-0c7217cdde317cfec"  # Ubuntu 22.04 LTS (us-east-1)
KEY_NAME="editur-ai-key"
REGION="us-east-1"
AVAILABILITY_ZONE="us-east-1a"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

echo "🚀 Quick Deploy - Editur AI Backend"
echo "===================================="

# Check existing security group
SECURITY_GROUP_NAME="${PROJECT_NAME}-sg"
SG_ID=$(aws ec2 describe-security-groups \
    --group-names $SECURITY_GROUP_NAME \
    --query 'SecurityGroups[0].GroupId' \
    --output text \
    --region $REGION 2>/dev/null || echo "None")

if [ "$SG_ID" = "None" ]; then
    log_info "Creating security group..."
    
    SG_ID=$(aws ec2 create-security-group \
        --group-name $SECURITY_GROUP_NAME \
        --description "Security group for Editur AI Backend" \
        --query 'GroupId' \
        --output text \
        --region $REGION)
    
    # Add rules
    MY_IP=$(curl -s https://checkip.amazonaws.com)/32
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 22 \
        --cidr $MY_IP \
        --region $REGION
    
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 \
        --region $REGION
    
    log_success "Security group created: $SG_ID"
else
    log_info "Using existing security group: $SG_ID"
fi

# Create user data script
USER_DATA=$(cat << 'EOF' | base64 -w 0
#!/bin/bash
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "Starting Editur AI Backend setup at $(date)"
apt-get update -y
apt-get install -y curl git

# Download and run setup script
cd /tmp
curl -L https://raw.githubusercontent.com/ZetaSoftdev/video_clip_generator/main/ec2-deployment/setup-server.sh -o setup-server.sh
chmod +x setup-server.sh

# Run as ubuntu user
su - ubuntu -c "cd /tmp && ./setup-server.sh"

echo "Setup completed at $(date)"
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
echo ""
echo "🔗 Your API will be available at:"
echo "   🌐 API: http://$PUBLIC_IP/"
echo "   📚 Docs: http://$PUBLIC_IP/docs"
echo "   ❤️  Health: http://$PUBLIC_IP/health"
echo ""
echo "💻 SSH Access:"
echo "   ssh -i editur-ai-key.pem ubuntu@$PUBLIC_IP"
echo ""
echo "📊 Monitor Setup Progress:"
echo "   ssh -i editur-ai-key.pem ubuntu@$PUBLIC_IP 'tail -f /var/log/user-data.log'"

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
  "ssh_command": "ssh -i editur-ai-key.pem ubuntu@$PUBLIC_IP",
  "api_url": "http://$PUBLIC_IP/",
  "docs_url": "http://$PUBLIC_IP/docs",
  "health_url": "http://$PUBLIC_IP/health"
}
EOF

echo ""
echo "💰 Estimated Monthly Cost: ~\$11-15"
echo "🔧 Deployment info saved to: deployment-info.json"
echo ""
log_success "Deployment initiated successfully!"

echo ""
echo "⏱️  Please wait 5-10 minutes for complete setup, then test:"
echo "   curl http://$PUBLIC_IP/health"