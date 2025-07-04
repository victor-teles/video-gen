# Architecture Blueprint - Video Clip Generator

## Project Overview
Video Clip Generator is a FastAPI-based application that uses AI to automatically generate video clips from long-form content with intelligent cropping and word-level captions.

## Core Components

### API Layer
- **main.py** - FastAPI application entry point
- **start_api.py** - Alternative startup script with enhanced checks
- **models.py** - Pydantic models and database schemas
- **config.py** - Configuration management
- **database.py** - Database connection and session management

### Processing Layer
- **clip_generator.py** - Core video processing logic with AI integration
- **tasks.py** - Celery background tasks for video processing
- **storage_handler.py** - Unified storage management (local/S3)

### Storage
- **Local Storage**: ./storage/ directory for development
- **S3 Storage**: AWS S3 buckets for production (uploads/, processing/, results/)

### Database
- **Development**: SQLite (./clips.db)
- **Production**: PostgreSQL via AWS RDS

### Dependencies
- **Core**: FastAPI, SQLAlchemy, Celery, Redis
- **Video Processing**: ClipsAI, WhisperX, OpenCV, YOLO v8
- **Cloud**: boto3 for AWS S3 integration

## Deployment Architecture

### AWS Fargate Deployment
- **Infrastructure**: CloudFormation templates in deployment/
- **Containers**: Separate API and Worker containers
- **Storage**: S3 buckets with lifecycle policies
- **Load Balancer**: Application Load Balancer for API
- **Database**: RDS PostgreSQL

### CI/CD Pipeline
- **GitHub Actions**: .github/workflows/deploy.yml
- **Stages**: build-and-test → deploy-infrastructure → build-and-push → deploy-application
- **Registry**: Amazon ECR for container images

## File Registry

### Created Files
- deployment/s3_setup.bat - S3 bucket setup script
- deployment/s3_storage.py - S3 operations class
- deployment/list_s3_files.py - S3 bucket inspection tool
- deployment/README.md - Deployment documentation
- deployment/DOMAIN_SETUP.md - Custom domain configuration guide
- storage_handler.py - Storage abstraction layer
- .github/workflows/deploy.yml - CI/CD pipeline

### Environment Configuration
- STORAGE_TYPE (local/s3)
- AWS credentials for S3
- Database URLs for SQLite/PostgreSQL
- Redis URL for Celery

## Endpoints
- Base URL: https://api.trod.ai (production) / http://localhost:8000 (development)
- POST /api/upload-video - Main video processing endpoint
- GET /api/status/{job_id} - Job status checking
- GET /api/download/clips/{job_id}/{filename} - Download processed clips
- GET /api/download/captions/{job_id}/{filename} - Download caption files
- GET /api/health - Health check endpoint
- GET /docs - API documentation

## TODO Tracking
- [x] Fix CI build-and-test import errors  
- [x] Fix AWS credentials configuration
- [x] Fix CloudFormation Redis endpoint reference
- [x] Fix deployment order (infrastructure → images → services)
- [x] Fix cleanup-on-failure error handling
- [x] Add HTTPS support to load balancer for custom domain
- [x] Create domain setup documentation  
- [x] Fix CloudFormation resource naming conflict for load balancer listeners
- [ ] Monitor infrastructure deployment with HTTPS changes
- [ ] Get load balancer DNS name from deployed infrastructure
- [ ] Configure external DNS records for api.trod.ai
- [ ] Configure SSL at external provider level
- [ ] Test domain configuration and HTTPS endpoints
- [ ] Update CORS settings for production domain
- [ ] Test video processing functionality on custom domain
- [ ] Implement comprehensive error handling
- [ ] Add video processing progress tracking
- [ ] Enhance S3 security policies
- [ ] Add API rate limiting
- [ ] Implement user authentication 