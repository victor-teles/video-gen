#!/bin/bash

# Production On-Demand Deployment Script for Editur AI Backend with Full AI Models
# Direct on-demand instance launch for guaranteed availability

set -e

PROJECT_NAME="editur-ai"
INSTANCE_TYPE="t3.medium"
AMI_ID="ami-0c7217cdde317cfec"  # Ubuntu 22.04 LTS (us-east-1)
KEY_NAME="editur-ai-key"
REGION="us-east-1"
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

echo "🚀 Production On-Demand Deploy - Editur AI Backend (Full AI Models)"
echo "=================================================================="
echo "Storage: ${STORAGE_SIZE}GB | Instance: ${INSTANCE_TYPE} | Full AI Stack"

# Use existing security group
SECURITY_GROUP_NAME="${PROJECT_NAME}-sg"
SG_ID=$(aws ec2 describe-security-groups \
    --group-names $SECURITY_GROUP_NAME \
    --query 'SecurityGroups[0].GroupId' \
    --output text \
    --region $REGION 2>/dev/null || echo "None")

if [ "$SG_ID" = "None" ]; then
    log_error "Security group not found. Please run the spot deployment script first to create it."
    exit 1
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

# Launch on-demand instance
log_info "Launching production on-demand instance..."

INSTANCE_ID=$(aws ec2 run-instances \
    --image-id "$AMI_ID" \
    --count 1 \
    --instance-type "$INSTANCE_TYPE" \
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
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=editur-ai-production},{Key=Project,Value=EditurAI},{Key=Environment,Value=production}]" \
    --query 'Instances[0].InstanceId' \
    --output text \
    --region $REGION)

if [ -z "$INSTANCE_ID" ] || [ "$INSTANCE_ID" = "None" ]; then
    log_error "Failed to launch production instance"
    exit 1
fi

log_success "Production instance launched: $INSTANCE_ID"

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
echo "   Instance Type: $INSTANCE_TYPE"
echo "   Storage: ${STORAGE_SIZE}GB"
echo "   Deployment Type: On-Demand Instance"
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
  "key_name": "$KEY_NAME",
  "security_group_id": "$SG_ID",
  "region": "$REGION",
  "instance_type": "$INSTANCE_TYPE",
  "storage_size": "$STORAGE_SIZE",
  "deployment_type": "production_ondemand",
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
echo "   Monthly: ~\$25-30 (On-demand with full AI capabilities)"
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