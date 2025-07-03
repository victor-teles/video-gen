# Domain Setup Guide - api.trod.ai

## Overview
This guide explains how to configure your custom domain `api.trod.ai` with your Video Clip Generator application deployed on AWS.

## Prerequisites
- ✅ Domain `trod.ai` owned and managed externally
- ✅ SSL certificate managed externally
- ✅ DNS management access for your domain
- ✅ Application deployed on AWS Fargate

## Step 1: Deploy Infrastructure Updates

The CloudFormation infrastructure has been updated to support HTTPS traffic on port 443. Deploy the updated infrastructure:

```bash
cd deployment
./deploy.sh
```

## Step 2: Get Load Balancer DNS Name

After deployment, get the AWS Load Balancer DNS name from CloudFormation outputs:

```bash
aws cloudformation describe-stacks \
  --stack-name video-clip-generator-production-infrastructure \
  --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNSName`].OutputValue' \
  --output text
```

This will return something like: `vcg-production-alb-1234567890.us-east-1.elb.amazonaws.com`

## Step 3: Configure DNS Records

In your external DNS management panel (where you manage `trod.ai`), create the following records:

### A Record (Recommended)
```
Type: A
Name: api
TTL: 300 (5 minutes)
Value: [IP address of the load balancer]
```

### CNAME Record (Alternative)
```
Type: CNAME  
Name: api
TTL: 300 (5 minutes)
Value: vcg-production-alb-1234567890.us-east-1.elb.amazonaws.com
```

**Note**: Replace the value with your actual load balancer DNS name from Step 2.

## Step 4: Configure SSL/HTTPS

Since you manage SSL externally, configure your SSL provider to:

1. **SSL Certificate**: Ensure your certificate covers `api.trod.ai`
2. **Origin Server**: Point to your AWS Load Balancer
3. **SSL Mode**: Set to "Full" or "Full (Strict)" if supported
4. **Port Configuration**: 
   - HTTPS (443) → HTTP (80) to load balancer
   - OR HTTPS (443) → HTTPS (443) to load balancer

## Step 5: Update Application Configuration

Update your environment variables to include your domain:

```bash
# Add to your .env or environment configuration
ALLOWED_ORIGINS=https://api.trod.ai,http://localhost:3000
API_BASE_URL=https://api.trod.ai
```

## Step 6: Test Configuration

Once DNS propagates (usually 5-15 minutes), test your endpoints:

```bash
# Health check
curl https://api.trod.ai/api/health

# API documentation  
curl https://api.trod.ai/docs

# Root endpoint
curl https://api.trod.ai/
```

## Load Balancer Configuration

Your AWS Application Load Balancer is configured with:

- ✅ HTTP Listener (Port 80): Accepts traffic and forwards to containers
- ✅ HTTPS Listener (Port 443): Accepts HTTPS traffic and forwards to containers  
- ✅ Target Group: Routes to your FastAPI containers on port 8000
- ✅ Health Checks: `/api/health` endpoint with 10s intervals

## API Endpoints

Once configured, your API will be available at:

- **Base URL**: `https://api.trod.ai`
- **Documentation**: `https://api.trod.ai/docs`
- **Health Check**: `https://api.trod.ai/api/health`
- **Upload Video**: `POST https://api.trod.ai/api/upload-video`
- **Check Status**: `GET https://api.trod.ai/api/status/{job_id}`
- **Download**: `GET https://api.trod.ai/api/download/clips/{job_id}/{filename}`

## Troubleshooting

### DNS Issues
```bash
# Check DNS resolution
nslookup api.trod.ai
dig api.trod.ai

# Check if domain points to load balancer
curl -I https://api.trod.ai/api/health
```

### SSL Issues
- Verify your SSL certificate includes `api.trod.ai`
- Check SSL configuration points to correct load balancer
- Ensure SSL mode allows HTTP backend connections

### Application Issues
```bash
# Check CloudWatch logs
aws logs tail /ecs/video-clip-generator-production --follow

# Check ECS service health
aws ecs describe-services --cluster vcg-production --services vcg-production-api
```

### CORS Issues
If you have frontend applications, update `ALLOWED_ORIGINS`:
```bash
ALLOWED_ORIGINS=https://api.trod.ai,https://yourfrontend.com,http://localhost:3000
```

## Security Considerations

1. **HTTPS Only**: Redirect all HTTP traffic to HTTPS at your SSL provider level
2. **CORS**: Configure specific allowed origins instead of "*" for production
3. **Rate Limiting**: Consider implementing rate limiting for your API
4. **API Keys**: Consider adding API authentication for production use

## Monitoring

Monitor your domain setup with:

- **Uptime Monitoring**: Set up monitoring for `https://api.trod.ai/api/health`
- **SSL Monitoring**: Monitor certificate expiration
- **DNS Monitoring**: Monitor DNS resolution
- **CloudWatch**: Monitor ECS service health and logs 