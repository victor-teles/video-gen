#!/bin/bash

# EC2 Server Setup Script for Editur AI Backend
# This script sets up the entire backend on a fresh Ubuntu EC2 instance

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    log_error "Please don't run this script as root. Run as ubuntu user."
    exit 1
fi

log_info "Starting Editur AI Backend Setup on EC2..."

# Update system
log_info "Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

# Install essential packages
log_info "Installing essential packages..."
sudo apt-get install -y \
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
    libhdf5-dev

log_success "Essential packages installed"

# Create application directory
log_info "Setting up application directory..."
sudo mkdir -p /opt/editur-ai
sudo chown ubuntu:ubuntu /opt/editur-ai
cd /opt/editur-ai

# Clone the repository
log_info "Cloning backend repository..."
if [ ! -d "backend" ]; then
    git clone https://github.com/ZetaSoftdev/video_clip_generator backend
else
    log_warning "Backend directory already exists, pulling latest changes..."
    cd backend && git pull && cd ..
fi

cd backend

# Create Python virtual environment
log_info "Creating Python virtual environment..."
python3.10 -m venv venv
source venv/bin/activate

# Upgrade pip
log_info "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
log_info "Installing Python dependencies (this may take 10-15 minutes)..."
pip install -r requirements.txt

log_success "Python dependencies installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    log_info "Creating .env file from template..."
    cp env.template .env
    log_warning "Please edit /opt/editur-ai/backend/.env with your actual API keys and settings"
fi

# Setup database
log_info "Initializing database..."
python -c "
from database import init_database
init_database()
print('Database initialized successfully')
"

# Configure Redis
log_info "Configuring Redis..."
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Test Redis connection
redis-cli ping || log_error "Redis is not running properly"

# Create systemd service files
log_info "Creating systemd service files..."

# API Service
sudo tee /etc/systemd/system/editur-api.service > /dev/null <<EOF
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
EOF

# Worker Service
sudo tee /etc/systemd/system/editur-worker.service > /dev/null <<EOF
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
EOF

# Configure Nginx
log_info "Configuring Nginx..."
sudo tee /etc/nginx/sites-available/editur-ai > /dev/null <<EOF
server {
    listen 80;
    server_name _;  # Accept any hostname
    
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
        
        # For file uploads
        proxy_request_buffering off;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/api/health;
        proxy_set_header Host \$host;
    }
    
    # API documentation
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host \$host;
    }
}
EOF

# Enable Nginx site
sudo ln -sf /etc/nginx/sites-available/editur-ai /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Reload systemd and enable services
log_info "Enabling and starting services..."
sudo systemctl daemon-reload
sudo systemctl enable editur-api editur-worker nginx
sudo systemctl restart nginx

# Start services
sudo systemctl start editur-api
sudo systemctl start editur-worker

# Wait a moment for services to start
sleep 5

# Check service status
log_info "Checking service status..."
sudo systemctl status editur-api --no-pager -l
sudo systemctl status editur-worker --no-pager -l
sudo systemctl status nginx --no-pager -l

# Create spot interruption handler
log_info "Creating spot interruption handler..."
tee /opt/editur-ai/spot-interrupt-handler.sh > /dev/null <<EOF
#!/bin/bash
# Monitor for spot interruption notices
while true; do
    if curl -s http://169.254.169.254/latest/meta-data/spot/instance-action 2>/dev/null | grep -q action; then
        echo "Spot interruption detected! Gracefully stopping services..."
        sudo systemctl stop editur-api editur-worker
        # Send notification if webhook is configured
        if [ ! -z "\$WEBHOOK_URL" ]; then
            curl -X POST "\$WEBHOOK_URL" -d "Spot instance interrupted: \$(curl -s http://169.254.169.254/latest/meta-data/instance-id)"
        fi
        exit 0
    fi
    sleep 5
done
EOF

chmod +x /opt/editur-ai/spot-interrupt-handler.sh

# Add to crontab
(crontab -l 2>/dev/null; echo "@reboot /opt/editur-ai/spot-interrupt-handler.sh &") | crontab -

# Create log rotation
sudo tee /etc/logrotate.d/editur-ai > /dev/null <<EOF
/var/log/editur-ai/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
    postrotate
        systemctl reload editur-api editur-worker
    endscript
}
EOF

# Create monitoring script
log_info "Creating monitoring script..."
tee /opt/editur-ai/monitor.sh > /dev/null <<EOF
#!/bin/bash
# Simple monitoring script

echo "=== Editur AI Backend Status ==="
echo "Time: \$(date)"
echo ""

echo "=== System Resources ==="
free -h
df -h /
echo ""

echo "=== Service Status ==="
systemctl is-active editur-api && echo "API: Running ✓" || echo "API: Stopped ✗"
systemctl is-active editur-worker && echo "Worker: Running ✓" || echo "Worker: Stopped ✗"
systemctl is-active nginx && echo "Nginx: Running ✓" || echo "Nginx: Stopped ✗"
systemctl is-active redis && echo "Redis: Running ✓" || echo "Redis: Stopped ✗"
echo ""

echo "=== API Health Check ==="
curl -s http://localhost/health || echo "API health check failed"
echo ""

echo "=== Recent Logs (last 10 lines) ==="
journalctl -u editur-api --no-pager -n 10
echo ""
journalctl -u editur-worker --no-pager -n 10
EOF

chmod +x /opt/editur-ai/monitor.sh

# Final health check
log_info "Performing final health check..."
sleep 10

if curl -s http://localhost/health > /dev/null; then
    log_success "✅ Editur AI Backend is running successfully!"
    echo ""
    echo "🌐 Your API is available at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/"
    echo "📚 API Documentation: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/docs"
    echo "❤️  Health Check: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/health"
    echo ""
    echo "📋 Next Steps:"
    echo "1. Edit /opt/editur-ai/backend/.env with your API keys"
    echo "2. Restart services: sudo systemctl restart editur-api editur-worker"
    echo "3. Monitor with: /opt/editur-ai/monitor.sh"
    echo "4. Check logs: sudo journalctl -u editur-api -f"
    echo ""
    echo "💰 Cost Optimization Tips:"
    echo "- Stop instance when not in use: aws ec2 stop-instances --instance-ids i-your-instance-id"
    echo "- Set up auto-scaling based on usage"
    echo "- Monitor costs with AWS Cost Explorer"
else
    log_error "❌ Health check failed. Check the logs:"
    echo "sudo journalctl -u editur-api -n 50"
    echo "sudo journalctl -u editur-worker -n 50"
fi

log_success "Setup complete!"