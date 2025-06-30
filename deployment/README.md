# 🚀 AWS Fargate Deployment Guide

Complete guide to deploy Video Clip Generator to AWS Fargate with automatic CI/CD.

## 📋 Prerequisites

### ✅ Required Tools
- [AWS CLI](https://aws.amazon.com/cli/) configured with your credentials
- [Docker](https://www.docker.com/) installed and running
- [Git](https://git-scm.com/) for version control
- GitHub account with your repository

### ✅ AWS Setup
- AWS Account with billing enabled
- S3 bucket `trod-video-clips` (already created)
- AWS credentials with appropriate permissions
- Region: `us-east-1`

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   GitHub        │    │   AWS Fargate    │    │   Amazon S3     │
│                 │    │                  │    │                 │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │   Source    │ ├────┤ │     API      │ ├────┤ │   Videos    │ │
│ │    Code     │ │    │ │  (FastAPI)   │ │    │ │   Storage   │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ └─────────────┘ │
│                 │    │                  │    │                 │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │   CI/CD     │ ├────┤ │   Workers    │ │    │ │   Results   │ │
│ │ (Actions)   │ │    │ │  (Celery)    │ ├────┤ │   Storage   │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                       ┌──────────────────┐
                       │  Amazon Redis    │
                       │  (ElastiCache)   │
                       └──────────────────┘
```

## 🚀 Deployment Options

### Option 1: Automatic CI/CD (Recommended)

**Push to GitHub and let automation handle everything:**

1. **Add AWS Secrets to GitHub:**
   ```bash
   # Go to: GitHub Repository → Settings → Secrets and Variables → Actions
   # Add these secrets:
   
   AWS_ACCESS_KEY_ID: your-access-key-id
   AWS_SECRET_ACCESS_KEY: your-secret-access-key
   ```

2. **Push to Main Branch:**
   ```bash
   git add .
   git commit -m "Deploy to AWS Fargate"
   git push origin main
   ```

3. **Monitor Deployment:**
   - Go to GitHub → Actions tab
   - Watch the deployment progress
   - Get your application URL from the deployment logs

### Option 2: Manual Deployment

**Deploy manually using the provided script:**

```bash
cd deployment
chmod +x deploy.sh
./deploy.sh
```

## 📁 Deployment Files

| File | Purpose |
|------|---------|
| `cloudformation-infrastructure.yml` | AWS infrastructure (VPC, ECS, Load Balancer) |
| `cloudformation-application.yml` | Application resources (ECR, Task Definitions) |
| `.github/workflows/deploy.yml` | GitHub Actions CI/CD pipeline |
| `deploy.sh` | Manual deployment script |
| `cleanup.sh` | Resource cleanup script |

## 🔧 Configuration

### Environment Variables (Production)

The deployment automatically configures these production settings:

```yaml
# Storage
STORAGE_TYPE: s3
S3_BUCKET_NAME: trod-video-clips
AWS_REGION: us-east-1

# API
API_HOST: 0.0.0.0
API_PORT: 8000
DEBUG: false

# Processing
DEFAULT_NUM_CLIPS: 3
DEFAULT_RATIO: "16:9"
MAX_FILE_SIZE: 500

# AI Settings
WHISPER_MODEL_SIZE: base
YOLO_MODEL: yolov8n.pt
AI_DEVICE: cpu

# Worker Settings
CELERY_WORKER_CONCURRENCY: 1
CELERY_LOG_LEVEL: info
CELERY_TASK_TIME_LIMIT: 3600
```

### Resource Sizing

| Service | CPU | Memory | Instances | Purpose |
|---------|-----|--------|-----------|---------|
| API | 512 | 1GB | 1-10 (auto-scale) | Handle HTTP requests |
| Worker | 1024 | 2GB | 1-5 (auto-scale) | Process videos |
| Redis | t3.micro | - | 1 | Task queue |

## 📊 Monitoring & Management

### CloudWatch Logs
```bash
# View API logs
aws logs tail /ecs/video-clip-generator-production --follow

# View Worker logs  
aws logs tail /ecs/video-clip-generator-production --follow --filter-pattern "worker"
```

### Scaling Services
```bash
# Scale API instances
aws ecs update-service \
  --cluster video-clip-generator-production \
  --service video-clip-generator-production-api \
  --desired-count 2

# Scale Worker instances
aws ecs update-service \
  --cluster video-clip-generator-production \
  --service video-clip-generator-production-worker \
  --desired-count 2
```

### Health Checks
- **Application Health:** `http://your-load-balancer-url/api/health`
- **API Documentation:** `http://your-load-balancer-url/docs`
- **ECS Console:** AWS Console → ECS → Clusters → video-clip-generator-production

## 💰 Cost Estimation

**For 5-10 videos/day (MVP usage):**

| Service | Monthly Cost |
|---------|-------------|
| ECS Fargate (API) | $15-25 |
| ECS Fargate (Worker) | $20-30 |
| Application Load Balancer | $16 |
| ElastiCache Redis | $10 |
| ECR (Docker Images) | $2-5 |
| CloudWatch Logs | $2-5 |
| Data Transfer | $5-10 |
| **Total** | **$75-100/month** |

**Notes:**
- S3 storage costs separate (minimal for 5-10 videos)
- Spot instances used for 80% cost savings
- Auto-scaling reduces costs during low usage

## 🔒 Security Features

### Network Security
- VPC with private subnets
- Security groups restricting traffic
- Load balancer SSL termination (when certificate added)

### Application Security
- IAM roles with minimal permissions
- ECR image scanning enabled
- Secrets managed via environment variables
- No hardcoded credentials

### Data Security
- Redis encryption at rest
- S3 bucket access via IAM roles
- CloudWatch logs retention (30 days)

## 🚨 Troubleshooting

### Common Issues

**1. Deployment Fails:**
```bash
# Check CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name video-clip-generator-production-infrastructure

# Check ECS service status
aws ecs describe-services \
  --cluster video-clip-generator-production \
  --services video-clip-generator-production-api
```

**2. Application Not Responding:**
```bash
# Check task logs
aws logs tail /ecs/video-clip-generator-production --follow

# Check task health
aws ecs describe-tasks \
  --cluster video-clip-generator-production \
  --tasks $(aws ecs list-tasks --cluster video-clip-generator-production --query 'taskArns[0]' --output text)
```

**3. High Costs:**
```bash
# Scale down for testing
aws ecs update-service \
  --cluster video-clip-generator-production \
  --service video-clip-generator-production-api \
  --desired-count 1

aws ecs update-service \
  --cluster video-clip-generator-production \
  --service video-clip-generator-production-worker \
  --desired-count 1
```

### Getting Support

1. **Check GitHub Actions logs** for deployment issues
2. **Review CloudWatch logs** for application errors
3. **Monitor CloudFormation events** for infrastructure issues
4. **Check ECS service events** for container problems

## 🧹 Cleanup

**To delete all AWS resources and stop charges:**

```bash
cd deployment
chmod +x cleanup.sh
./cleanup.sh
```

**This will delete:**
- ECS Cluster and Services
- Load Balancer and VPC
- ECR Repositories
- Redis Cluster
- CloudWatch Logs

**Note:** S3 bucket is preserved to keep your videos safe.

## 🔄 Updates and Redeployment

### Automatic Updates
- Push to `main` branch triggers automatic deployment
- GitHub Actions handles building and deploying new versions
- Zero-downtime rolling updates

### Manual Updates
```bash
# Redeploy with latest code
cd deployment
./deploy.sh

# Or force new deployment without code changes
aws ecs update-service \
  --cluster video-clip-generator-production \
  --service video-clip-generator-production-api \
  --force-new-deployment
```

## 🌐 Adding Custom Domain

**To use your own domain instead of AWS-generated URL:**

1. **Get SSL Certificate:**
   ```bash
   # Request certificate in ACM
   aws acm request-certificate \
     --domain-name yourdomain.com \
     --validation-method DNS
   ```

2. **Update CloudFormation:**
   - Add certificate ARN to `cloudformation-infrastructure.yml`
   - Add HTTPS listener to load balancer
   - Update Route53 DNS records

3. **Redeploy:**
   ```bash
   ./deploy.sh
   ```

---

## 🎉 Success! 

Your Video Clip Generator is now running on AWS Fargate with:
- ✅ Automatic scaling
- ✅ High availability  
- ✅ Production monitoring
- ✅ Cost optimization
- ✅ CI/CD pipeline

**Happy video processing! 🎬✨** 