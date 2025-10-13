# 🚀 AWS EC2 Spot Deployment Guide for Editur AI Backend

## Overview
This guide walks you through deploying the Editur AI backend on AWS EC2 Spot instances for **maximum cost savings** (~$10-15/month vs $75-100 for full ECS).

## 📋 Prerequisites

### 1. AWS Account Setup
- ✅ Fresh AWS account created
- ✅ Credit card added for billing
- ✅ Root access or IAM user with full EC2/S3 permissions

### 2. Local Tools Required
- ✅ AWS CLI installed
- ✅ SSH client (Terminal/PuTTY)
- ✅ Git (if cloning locally)

### 3. API Keys (for full functionality)
- 🔑 OpenAI API key (for GPT-4 and TTS)
- 🔑 Replicate API token (for image generation)
- 🔑 AWS Access Keys (for S3 storage)

## 🛠️ Step-by-Step Deployment

### Step 1: Install and Configure AWS CLI

```bash
# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure with your AWS credentials
aws configure
```

**Enter when prompted:**
- AWS Access Key ID: `[Your Access Key]`
- AWS Secret Access Key: `[Your Secret Key]`
- Default region: `us-east-1`
- Default output format: `json`

### Step 2: Clone Repository and Prepare Deployment

```bash
# Clone the backend repository
git clone https://github.com/ZetaSoftdev/video_clip_generator
cd video_clip_generator

# Make deployment script executable
chmod +x ec2-deployment/deploy-ec2-spot.sh
```

### Step 3: Run Deployment Script

```bash
# Run the automated deployment
./ec2-deployment/deploy-ec2-spot.sh
```

**What this script does:**
1. ✅ Creates security groups with proper ports
2. ✅ Requests EC2 spot instance (70% cost savings)
3. ✅ Automatically installs all dependencies
4. ✅ Sets up systemd services for auto-restart
5. ✅ Configures Nginx reverse proxy
6. ✅ Creates monitoring and logging

**Expected output:**
```
🎉 Editur AI Backend Deployment Started!

📋 Instance Details:
   Instance ID: i-1234567890abcdef0
   Public IP: 3.123.45.67
   Instance Type: t3.medium
   Spot Price: $0.0416/hour
   Key Pair: editur-ai-20241013

🔗 Access URLs (available after setup completes):
   🌐 API: http://3.123.45.67/
   📚 Docs: http://3.123.45.67/docs
   ❤️  Health: http://3.123.45.67/health
```

### Step 4: Configure Environment Variables

**Wait 5-10 minutes for initial setup, then:**

```bash
# SSH into your server
ssh -i editur-ai-20241013.pem ubuntu@3.123.45.67

# Edit environment configuration
sudo nano /opt/editur-ai/backend/.env
```

**Required configurations:**

```bash
# AWS S3 (REQUIRED)
S3_BUCKET_NAME=editur-ai-storage-YOUR_UNIQUE_ID
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key_here

# OpenAI (for faceless videos)
OPENAI_API_KEY=sk-your_openai_api_key_here

# Replicate (for image generation)
REPLICATE_API_TOKEN=r8_your_replicate_token_here
```

### Step 5: Create S3 Bucket

```bash
# Create unique S3 bucket name
BUCKET_NAME="editur-ai-storage-$(date +%s)"

# Create bucket
aws s3 mb s3://$BUCKET_NAME --region us-east-1

# Set CORS policy for web uploads
aws s3api put-bucket-cors --bucket $BUCKET_NAME --cors-configuration file://cors-policy.json
```

**cors-policy.json:**
```json
{
  "CORSRules": [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET", "POST", "PUT", "DELETE"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3000
    }
  ]
}
```

### Step 6: Restart Services

```bash
# Update .env with your S3 bucket name
sudo sed -i "s/editur-ai-storage-YOUR_UNIQUE_ID/$BUCKET_NAME/" /opt/editur-ai/backend/.env

# Restart services to pick up new configuration
sudo systemctl restart editur-api editur-worker

# Check status
/opt/editur-ai/monitor.sh
```

### Step 7: Test Your API

```bash
# Test health endpoint
curl http://YOUR_IP/health

# Expected response:
{"status": "healthy", "timestamp": "2024-10-13T10:30:00Z"}

# Test API documentation
# Visit: http://YOUR_IP/docs
```

## 🧪 Testing Your Deployment

### 1. Upload and Process Video
```bash
# Test video upload (replace with your IP)
curl -X POST "http://YOUR_IP/api/upload-video" \
  -F "file=@test-video.mp4" \
  -F "num_clips=2" \
  -F "ratio=9:16"

# Response:
{"processing_id": "abc123", "status": "queued", "message": "Video uploaded successfully"}
```

### 2. Check Processing Status
```bash
curl http://YOUR_IP/api/status/abc123

# Response:
{"processing_id": "abc123", "status": "processing", "progress": 45}
```

### 3. Generate Faceless Video
```bash
curl -X POST "http://YOUR_IP/api/faceless-video/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "story_title": "Amazing Facts About Space",
    "story_description": "Discover incredible facts about our universe",
    "voice_id": "nova",
    "image_style": "photorealistic"
  }'
```

## 💰 Cost Optimization

### Current Setup Costs (~$10-15/month):
- **EC2 t3.medium Spot**: $7-10/month
- **S3 Storage (50GB)**: $1-2/month  
- **Data Transfer**: $2-3/month
- **Total**: $10-15/month

### Additional Cost-Saving Tips:

1. **Stop Instance When Not in Use**
```bash
# Stop instance (keeps storage, stops compute charges)
aws ec2 stop-instances --instance-ids i-1234567890abcdef0

# Start when needed
aws ec2 start-instances --instance-ids i-1234567890abcdef0
```

2. **Set Up S3 Lifecycle Policies**
```bash
# Auto-delete old files to save storage costs
aws s3api put-bucket-lifecycle-configuration \
  --bucket $BUCKET_NAME \
  --lifecycle-configuration file://lifecycle-policy.json
```

3. **Monitor Costs**
```bash
# Set up billing alert
aws cloudwatch put-metric-alarm \
  --alarm-name "EditurAI-BudgetAlert" \
  --alarm-description "Alert when monthly cost exceeds $20" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 20 \
  --comparison-operator GreaterThanThreshold
```

## 🔧 Management Commands

### Check System Status
```bash
ssh -i your-key.pem ubuntu@YOUR_IP '/opt/editur-ai/monitor.sh'
```

### View Logs
```bash
# API logs
ssh -i your-key.pem ubuntu@YOUR_IP 'sudo journalctl -u editur-api -f'

# Worker logs
ssh -i your-key.pem ubuntu@YOUR_IP 'sudo journalctl -u editur-worker -f'

# System logs
ssh -i your-key.pem ubuntu@YOUR_IP 'tail -f /var/log/user-data.log'
```

### Restart Services
```bash
ssh -i your-key.pem ubuntu@YOUR_IP 'sudo systemctl restart editur-api editur-worker'
```

### Update Code
```bash
ssh -i your-key.pem ubuntu@YOUR_IP
cd /opt/editur-ai/backend
git pull
sudo systemctl restart editur-api editur-worker
```

## 🔒 Security Best Practices

### 1. Restrict SSH Access
```bash
# Update security group to only allow your IP
MY_IP=$(curl -s https://checkip.amazonaws.com)/32
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 22 \
  --cidr $MY_IP
```

### 2. Enable CloudWatch Monitoring
```bash
# Install CloudWatch agent for detailed metrics
ssh -i your-key.pem ubuntu@YOUR_IP
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb
```

### 3. Set Up Automated Backups
```bash
# Create daily snapshots
aws ec2 create-snapshot \
  --volume-id vol-xxxxx \
  --description "Daily backup $(date +%Y-%m-%d)"
```

## 🚨 Troubleshooting

### Problem: API Not Responding
```bash
# Check service status
ssh -i your-key.pem ubuntu@YOUR_IP 'sudo systemctl status editur-api'

# Check logs
ssh -i your-key.pem ubuntu@YOUR_IP 'sudo journalctl -u editur-api -n 50'

# Restart if needed
ssh -i your-key.pem ubuntu@YOUR_IP 'sudo systemctl restart editur-api'
```

### Problem: High Costs
```bash
# Check AWS costs
aws ce get-cost-and-usage \
  --time-period Start=2024-10-01,End=2024-10-31 \
  --granularity MONTHLY \
  --metrics BlendedCost

# Stop instance if not in use
aws ec2 stop-instances --instance-ids i-xxxxx
```

### Problem: Spot Instance Interrupted
```bash
# Check if instance was terminated
aws ec2 describe-instances --instance-ids i-xxxxx

# If terminated, run deployment script again
./ec2-deployment/deploy-ec2-spot.sh
```

### Problem: Out of Storage
```bash
# Check disk usage
ssh -i your-key.pem ubuntu@YOUR_IP 'df -h'

# Clean up old files
ssh -i your-key.pem ubuntu@YOUR_IP 'sudo find /opt/editur-ai/backend/storage -mtime +7 -delete'
```

## 📈 Scaling Up When Needed

### When traffic increases:
1. **Scale vertically**: Change instance type to t3.large or t3.xlarge
2. **Scale horizontally**: Add more instances behind a load balancer
3. **Migrate to ECS**: Use your existing CloudFormation templates

### Migration path:
```
EC2 Spot ($10/month) → ECS Fargate Spot ($30/month) → Full ECS ($75/month)
```

## 🎯 Next Steps

1. **✅ Test all API endpoints** with your frontend
2. **✅ Set up domain name** (optional) using Route53
3. **✅ Enable HTTPS** with Let's Encrypt
4. **✅ Set up monitoring** and alerts
5. **✅ Plan for backups** and disaster recovery

## 🆘 Support

**If you encounter issues:**
1. Check the troubleshooting section above
2. Review AWS CloudWatch logs
3. Check GitHub issues for similar problems
4. Monitor AWS costs regularly

**Remember:** This setup saves you ~$60-85/month compared to full ECS deployment while providing the same functionality!