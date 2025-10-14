#!/bin/bash

# Enhanced Production Deployment Script for Editur AI Backend with Full AI Models
# Includes fallback options for better spot instance availability

set -e

PROJECT_NAME="editur-ai"
# Try multiple instance types for better availability
INSTANCE_TYPES=("t3.medium" "t3a.medium" "t2.medium" "c5.large")
SPOT_PRICE="0.08"  # Higher price for better availability
AMI_ID="ami-0c7217cdde317cfec"  # Ubuntu 22.04 LTS (us-east-1)
KEY_NAME="editur-ai-key"
REGION="us-east-1"
# Try multiple availability zones
AVAILABILITY_ZONES=("us-east-1a" "us-east-1b" "us-east-1c" "us-east-1d" "us-east-1e" "us-east-1f")
STORAGE_SIZE=50  # 50GB for production with AI models

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "🚀 Enhanced Production Deploy - Editur AI Backend (Full AI Models)"
echo "=================================================================="
echo "Storage: ${STORAGE_SIZE}GB | Multi-AZ & Multi-Instance | Full AI Stack"

# Use existing security group
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

# Create production user data script with full AI setup
USER_DATA=$(cat << 'EOF' | base64 -w 0
#!/bin/bash
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "Starting Editur AI Production Backend setup at $(date)"

# Update system
apt-get update -y
apt-get upgrade -y

# Install essential packages including AI/ML dependencies
apt-get install -y \
    python3.10 \
    python3-pip \
    python3.10-venv \
    redis-server \
    nginx \
    ffmpeg \
    git \
    curl \
    wget \
    htop \
    unzip \
    software-properties-common \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    pkg-config \
    libhdf5-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libjpeg-dev \
    libpng-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libatlas-base-dev \
    gfortran

echo "System packages installed successfully"

# Create application directory
mkdir -p /opt/editur-ai
chown ubuntu:ubuntu /opt/editur-ai
cd /opt/editur-ai

# Clone repository as ubuntu user
sudo -u ubuntu git clone https://github.com/ZetaSoftdev/video_clip_generator backend
cd backend

# Create Python virtual environment
sudo -u ubuntu python3.10 -m venv venv
sudo -u ubuntu /opt/editur-ai/backend/venv/bin/pip install --upgrade pip

echo "Installing Python dependencies (this will take 15-20 minutes)..."

# Install dependencies in order to avoid conflicts
sudo -u ubuntu /opt/editur-ai/backend/venv/bin/pip install wheel setuptools

# Install core dependencies first
sudo -u ubuntu /opt/editur-ai/backend/venv/bin/pip install \
    fastapi==0.115.6 \
    uvicorn[standard]==0.34.0 \
    python-multipart==0.0.20 \
    aiofiles==24.1.0

# Install database dependencies
sudo -u ubuntu /opt/editur-ai/backend/venv/bin/pip install \
    sqlalchemy==2.0.36 \
    alembic==1.16.2 \
    psycopg2-binary==2.9.9

# Install queue system
sudo -u ubuntu /opt/editur-ai/backend/venv/bin/pip install \
    celery==5.4.0 \
    redis==5.2.1 \
    flower==2.0.1

# Install environment variables
sudo -u ubuntu /opt/editur-ai/backend/venv/bin/pip install python-dotenv==1.0.1

# Install numerical computing
sudo -u ubuntu /opt/editur-ai/backend/venv/bin/pip install "numpy>=2.0.0"

# Install PyTorch (CPU version for cost optimization)
sudo -u ubuntu /opt/editur-ai/backend/venv/bin/pip install \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install OpenCV
sudo -u ubuntu /opt/editur-ai/backend/venv/bin/pip install "opencv-python>=4.8.0"

# Install YOLO
sudo -u ubuntu /opt/editur-ai/backend/venv/bin/pip install ultralytics

# Install video processing
sudo -u ubuntu /opt/editur-ai/backend/venv/bin/pip install "moviepy>=1.0.3"

# Install AI services
sudo -u ubuntu /opt/editur-ai/backend/venv/bin/pip install \
    "openai>=1.3.0" \
    "replicate>=0.22.0" \
    "pillow>=10.0.0"

# Install AWS dependencies
sudo -u ubuntu /opt/editur-ai/backend/venv/bin/pip install \
    "boto3>=1.34.0" \
    "botocore>=1.34.0" \
    "s3transfer>=0.10.0"

# Install additional dependencies
sudo -u ubuntu /opt/editur-ai/backend/venv/bin/pip install \
    python-magic==0.4.27 \
    "requests>=2.31.0"

# Install WhisperX
sudo -u ubuntu /opt/editur-ai/backend/venv/bin/pip install git+https://github.com/m-bain/whisperx.git

# Install ClipsAI
sudo -u ubuntu /opt/editur-ai/backend/venv/bin/pip install clipsai

echo "All Python dependencies installed successfully"

# Create production environment file
sudo -u ubuntu cp env.template .env
sudo -u ubuntu bash -c 'cat > .env << EOL
# Storage Configuration
STORAGE_TYPE=s3
S3_BUCKET_NAME=editur-ai-storage-$(date +%s)
AWS_REGION=us-east-1

# Database
DATABASE_URL=sqlite:///./editur.db

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
ALLOWED_ORIGINS=*

# Processing Settings
MAX_FILE_SIZE=524288000
DEFAULT_NUM_CLIPS=3
DEFAULT_RATIO=9:16
CELERY_WORKER_CONCURRENCY=2
CELERY_TASK_TIME_LIMIT=3600

# AI Model Settings
WHISPER_MODEL_SIZE=base
YOLO_MODEL=yolov8n.pt
AI_DEVICE=cpu

# Cost Optimization
VIDEO_CRF=23
AUDIO_BITRATE=128k
CLEANUP_UPLOADS_AFTER=24
CLEANUP_RESULTS_AFTER=72

# Faceless Video Settings
STORY_MODEL=gpt-4o-mini
TTS_MODEL=tts-1
IMAGE_MODEL=black-forest-labs/flux-schnell
MAX_FACELESS_VIDEOS_PER_USER=10
EOL'

# Initialize database
sudo -u ubuntu /opt/editur-ai/backend/venv/bin/python -c "
from database import init_database
init_database()
print('Database initialized successfully')
"

# Configure Redis
systemctl enable redis-server
systemctl start redis-server

# Create systemd service files
cat > /etc/systemd/system/editur-api.service << EOL
[Unit]
Description=Editur AI FastAPI Service
After=network.target redis.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/editur-ai/backend
Environment="PATH=/opt/editur-ai/backend/venv/bin:/usr/bin:/usr/local/bin"
ExecStart=/opt/editur-ai/backend/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOL

cat > /etc/systemd/system/editur-worker.service << EOL
[Unit]
Description=Editur AI Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/editur-ai/backend
Environment="PATH=/opt/editur-ai/backend/venv/bin:/usr/bin:/usr/local/bin"
ExecStart=/opt/editur-ai/backend/venv/bin/python -m celery -A tasks worker --loglevel=info --concurrency=2
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOL

# Configure Nginx
cat > /etc/nginx/sites-available/editur-ai << EOL
server {
    listen 80;
    server_name _;
    
    client_max_body_size 500M;
    client_body_timeout 300s;
    proxy_read_timeout 300s;
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_request_buffering off;
    }
}
EOL

ln -sf /etc/nginx/sites-available/editur-ai /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t

# Enable and start services
systemctl daemon-reload
systemctl enable editur-api editur-worker nginx
systemctl restart nginx
systemctl start editur-api
systemctl start editur-worker

# Wait and test
sleep 10

# Create monitoring script
sudo -u ubuntu cat > /opt/editur-ai/monitor.sh << EOL
#!/bin/bash
echo "=== Editur AI Production Backend Status ==="
echo "Time: \$(date)"
echo ""
echo "=== System Resources ==="
free -h
df -h /
echo ""
echo "=== Services ==="
systemctl is-active editur-api && echo "API: Running ✓" || echo "API: Stopped ✗"
systemctl is-active editur-worker && echo "Worker: Running ✓" || echo "Worker: Stopped ✗"
systemctl is-active nginx && echo "Nginx: Running ✓" || echo "Nginx: Stopped ✗"
systemctl is-active redis && echo "Redis: Running ✓" || echo "Redis: Stopped ✗"
echo ""
echo "=== API Health ==="
curl -s http://localhost/health || echo "API health check failed"
echo ""
echo "=== AI Models Status ==="
ls -la /opt/editur-ai/backend/*.pt 2>/dev/null || echo "YOLO model not found"
echo ""
echo "=== Recent Logs ==="
journalctl -u editur-api --no-pager -n 5
EOL

chmod +x /opt/editur-ai/monitor.sh

echo "Production setup completed at $(date)"
echo "All AI models and dependencies installed"
echo "Full video processing capabilities enabled"
EOF
)

# Function to try launching spot instance
try_spot_instance() {
    local instance_type=$1
    local az=$2
    
    log_info "Trying $instance_type in $az..."
    
    local spot_request=$(aws ec2 request-spot-instances \
        --spot-price "$SPOT_PRICE" \
        --instance-count 1 \
        --type "one-time" \
        --launch-specification "{
            \"ImageId\": \"$AMI_ID\",
            \"InstanceType\": \"$instance_type\",
            \"KeyName\": \"$KEY_NAME\",
            \"SecurityGroupIds\": [\"$SG_ID\"],
            \"UserData\": \"$USER_DATA\",
            \"Placement\": {
                \"AvailabilityZone\": \"$az\"
            },
            \"BlockDeviceMappings\": [{
                \"DeviceName\": \"/dev/sda1\",
                \"Ebs\": {
                    \"VolumeSize\": $STORAGE_SIZE,
                    \"VolumeType\": \"gp3\",
                    \"DeleteOnTermination\": true
                }
            }]
        }" \
        --query 'SpotInstanceRequests[0].SpotInstanceRequestId' \
        --output text \
        --region $REGION 2>/dev/null)
    
    if [ "$spot_request" != "None" ] && [ -n "$spot_request" ]; then
        echo "$spot_request"
        return 0
    else
        return 1
    fi
}

# Function to launch on-demand instance as fallback
launch_ondemand() {
    log_warning "Launching on-demand instance as fallback..."
    
    local instance_id=$(aws ec2 run-instances \
        --image-id "$AMI_ID" \
        --count 1 \
        --instance-type "t3.medium" \
        --key-name "$KEY_NAME" \
        --security-group-ids "$SG_ID" \
        --user-data "$USER_DATA" \
        --block-device-mappings "[{
            \"DeviceName\": \"/dev/sda1\",
            \"Ebs\": {
                \"VolumeSize\": $STORAGE_SIZE,
                \"VolumeType\": \"gp3\",
                \"DeleteOnTermination\": true
            }
        }]" \
        --tag-specifications "Resource=instance,Tags=[{Key=Name,Value=editur-ai-production},{Key=Project,Value=EditurAI},{Key=Environment,Value=production}]" \
        --query 'Instances[0].InstanceId' \
        --output text \
        --region $REGION)
    
    if [ -n "$instance_id" ] && [ "$instance_id" != "None" ]; then
        echo "$instance_id"
        return 0
    else
        return 1
    fi
}

# Try spot instances across multiple types and zones
log_info "Requesting production spot instance with ${STORAGE_SIZE}GB storage..."
SPOT_REQUEST_ID=""
FOUND_INSTANCE_TYPE=""
FOUND_AZ=""

for instance_type in "${INSTANCE_TYPES[@]}"; do
    for az in "${AVAILABILITY_ZONES[@]}"; do
        if SPOT_REQUEST_ID=$(try_spot_instance "$instance_type" "$az"); then
            FOUND_INSTANCE_TYPE="$instance_type"
            FOUND_AZ="$az"
            log_success "Spot request created: $SPOT_REQUEST_ID ($instance_type in $az)"
            break 2
        fi
        sleep 2
    done
done

INSTANCE_ID=""
INSTANCE_TYPE_USED=""

if [ -n "$SPOT_REQUEST_ID" ]; then
    # Wait for spot request to be fulfilled
    log_info "Waiting for spot instance to be fulfilled..."
    
    # Wait up to 5 minutes for spot fulfillment
    TIMEOUT=300
    ELAPSED=0
    while [ $ELAPSED -lt $TIMEOUT ]; do
        STATUS=$(aws ec2 describe-spot-instance-requests \
            --spot-instance-request-ids "$SPOT_REQUEST_ID" \
            --query 'SpotInstanceRequests[0].Status.Code' \
            --output text \
            --region $REGION)
        
        if [ "$STATUS" = "fulfilled" ]; then
            INSTANCE_ID=$(aws ec2 describe-spot-instance-requests \
                --spot-instance-request-ids "$SPOT_REQUEST_ID" \
                --query 'SpotInstanceRequests[0].InstanceId' \
                --output text \
                --region $REGION)
            INSTANCE_TYPE_USED="$FOUND_INSTANCE_TYPE"
            log_success "Spot instance fulfilled: $INSTANCE_ID"
            break
        elif [ "$STATUS" = "capacity-not-available" ] || [ "$STATUS" = "price-too-low" ]; then
            log_warning "Spot request failed: $STATUS"
            aws ec2 cancel-spot-instance-requests --spot-instance-request-ids "$SPOT_REQUEST_ID" --region $REGION >/dev/null 2>&1
            break
        fi
        
        sleep 10
        ELAPSED=$((ELAPSED + 10))
    done
fi

# Fallback to on-demand if spot failed
if [ -z "$INSTANCE_ID" ]; then
    log_warning "Spot instances not available, launching on-demand instance..."
    
    if INSTANCE_ID=$(launch_ondemand); then
        INSTANCE_TYPE_USED="t3.medium"
        log_success "On-demand instance launched: $INSTANCE_ID"
    else
        log_error "Failed to launch any instance"
        exit 1
    fi
fi

# Wait for instance to be running
log_info "Waiting for instance to be running..."
aws ec2 wait instance-running \
    --instance-ids "$INSTANCE_ID" \
    --region $REGION

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text \
    --region $REGION)

log_success "Production instance is running!"

echo ""
echo "🎉 Editur AI Production Backend Deployment Started!"
echo ""
echo "📋 Production Instance Details:"
echo "   Instance ID: $INSTANCE_ID"
echo "   Public IP: $PUBLIC_IP"
echo "   Instance Type: $INSTANCE_TYPE_USED"
echo "   Storage: ${STORAGE_SIZE}GB"
if [ -n "$SPOT_REQUEST_ID" ]; then
    echo "   Deployment Type: Spot Instance (Cost Optimized)"
    echo "   Spot Price: \$$SPOT_PRICE/hour"
else
    echo "   Deployment Type: On-Demand Instance"
fi
echo "   Key Pair: $KEY_NAME"
echo ""
echo "⏳ Production Setup in Progress (15-25 minutes)..."
echo "   Installing all AI models and dependencies"
echo "   - PyTorch (CPU optimized)"
echo "   - OpenCV"
echo "   - YOLO v8"
echo "   - WhisperX"
echo "   - ClipsAI"
echo "   - MoviePy"
echo "   - All production dependencies"
echo ""
echo "🔗 Production API URLs (available after setup):"
echo "   🌐 API: http://$PUBLIC_IP/"
echo "   📚 Docs: http://$PUBLIC_IP/docs"
echo "   ❤️  Health: http://$PUBLIC_IP/health"
echo ""
echo "💻 SSH Access:"
echo "   ssh -i editur-ai-key.pem ubuntu@$PUBLIC_IP"
echo ""
echo "📊 Monitor Production Setup:"
echo "   ssh -i editur-ai-key.pem ubuntu@$PUBLIC_IP 'tail -f /var/log/user-data.log'"
echo ""
echo "🔧 Production Management:"
echo "   ssh -i editur-ai-key.pem ubuntu@$PUBLIC_IP '/opt/editur-ai/monitor.sh'"

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
  "instance_type": "$INSTANCE_TYPE_USED",
  "storage_size": "$STORAGE_SIZE",
  "deployment_type": "production",
  "ai_models": ["yolo", "whisperx", "clipsai", "pytorch"],
  "ssh_command": "ssh -i editur-ai-key.pem ubuntu@$PUBLIC_IP",
  "api_url": "http://$PUBLIC_IP/",
  "docs_url": "http://$PUBLIC_IP/docs",
  "health_url": "http://$PUBLIC_IP/health",
  "monitor_command": "ssh -i editur-ai-key.pem ubuntu@$PUBLIC_IP '/opt/editur-ai/monitor.sh'"
}
EOF

echo ""
echo "💰 Production Cost Estimate:"
if [ -n "$SPOT_REQUEST_ID" ]; then
    echo "   Monthly: ~\$15-20 (Spot pricing with full AI capabilities)"
else
    echo "   Monthly: ~\$25-30 (On-demand with full AI capabilities)"
fi
echo "   Storage: 50GB included in estimate"
echo "   Processing: Optimized for CPU to minimize costs"
echo ""
echo "🔧 Deployment info saved to: deployment-info.json"
echo ""
log_success "Production deployment initiated successfully!"

echo ""
log_warning "⏱️  Please wait 15-25 minutes for complete production setup"
echo "   The system is installing full AI stack including:"
echo "   - All machine learning models"
echo "   - Video processing libraries"
echo "   - Complete dependency stack"
echo ""
echo "   Test when ready: curl http://$PUBLIC_IP/health"