# Video Clip Generator - Architecture Blueprint

## Overview
The Video Clip Generator is a FastAPI-based application that uses AI to automatically generate short clips from long-form videos. The system uses YOLO for object detection and auto-cropping, WhisperX for transcription, and ClipsAI for intelligent clip selection.

**NEW:** The system now also supports **Faceless Video Generation** - creating complete videos from text using AI-generated images and voice narration.

## System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   Celery Queue  │    │   Storage       │
│   (main.py)     │────│   (Redis)       │────│   (Local/S3)    │
│                 │    │                 │    │                 │
│ • Upload API    │    │ • Video Proc.   │    │ • Raw Videos    │
│ • Status API    │    │ • Faceless Gen. │    │ • Generated     │
│ • Download API  │    │ • Progress      │    │   Clips         │
│ • Faceless API  │    │   Tracking      │    │ • Faceless Vids │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         │              │   AI Pipeline   │              │
         └──────────────│                 │──────────────┘
                        │ • WhisperX      │
                        │ • ClipsAI       │
                        │ • YOLO v8       │
                        │ • OpenAI GPT-4  │
                        │ • Replicate     │
                        │ • OpenAI TTS    │
                        └─────────────────┘
```

## Core Components

### 1. API Layer (`main.py`)
- **FastAPI** application with comprehensive endpoints
- Input validation and error handling
- Authentication and rate limiting ready
- Storage-agnostic file handling (Local/S3)

#### Video Clip Generation Endpoints:
- `POST /api/upload-video` - Upload and queue video processing
- `GET /api/status/{processing_id}` - Get processing status and progress
- `GET /api/download/clips/{processing_id}/{filename}` - Download generated clips
- `GET /api/download/captions/{processing_id}/{filename}` - Download caption files

#### Faceless Video Generation Endpoints:
- `POST /api/faceless-video/generate` - Create faceless video from user input
- `GET /api/faceless-video/status/{processing_id}` - Get generation status
- `GET /api/download/faceless-video/{processing_id}` - Download generated video
- `GET /api/download/faceless-captions/{processing_id}` - Download caption JSON
- `GET /api/faceless-video/options` - Get available options (voices, styles, etc.)

### 2. Background Processing (`tasks.py`)
- **Celery** with Redis broker for async processing
- Progress tracking and status updates
- Comprehensive error handling and retry logic
- Memory cleanup and resource management

#### Video Clip Processing Pipeline:
1. Video transcription (WhisperX)
2. Intelligent clip detection (ClipsAI)
3. Object detection and auto-cropping (YOLO v8)
4. Caption generation (word-level timing)
5. Storage handling (Local/S3)

#### Faceless Video Generation Pipeline:
1. Story generation or enhancement (OpenAI GPT-4)
2. Storyboard creation with scene breakdown
3. Image generation for each scene (Replicate Flux)
4. Voice narration generation (OpenAI TTS)
5. Video composition without burned-in subtitles
6. Word-level caption file generation

### 3. AI Processing (`clip_generator.py`, `faceless_video_generator.py`)

#### Video Clip Generator:
- **WhisperX**: High-accuracy transcription with word-level timestamps
- **ClipsAI**: Intelligent clip selection based on content analysis
- **YOLO v8**: Object detection for automatic cropping to target ratios
- **OpenCV**: Video processing and manipulation

#### Faceless Video Generator:
- **OpenAI GPT-4**: Story generation and content enhancement
- **Replicate Flux**: High-quality AI image generation
- **OpenAI TTS**: Natural voice synthesis with multiple voice options
- **MoviePy**: Video composition and effects

### 4. Storage Management (`storage_handler.py`)
- Unified interface for local and S3 storage
- Automatic file organization and cleanup
- Presigned URL generation for secure downloads
- Storage migration capabilities

### 5. Database Models (`models.py`)

#### Video Clip Models:
- `ProcessingJob`: Track video processing jobs and metadata
- `GeneratedClip`: Store information about generated clips

#### Faceless Video Models:
- `FacelessVideoJob`: Track faceless video generation jobs
- `FacelessVideoScene`: Store individual scene information and metadata

## File Structure

```
Video_Clip_Generator/
├── main.py                      # FastAPI application and endpoints
├── tasks.py                     # Celery background tasks
├── clip_generator.py            # Video clip processing logic
├── faceless_video_generator.py  # Faceless video generation logic
├── models.py                    # Database models (SQLAlchemy)
├── database.py                  # Database configuration
├── storage_handler.py           # Storage abstraction layer
├── config.py                    # Configuration management
├── requirements.txt             # Python dependencies
├── env.template                 # Environment variables template
├── ARCHITECTURE_BLUEPRINT.md    # This file
├── CHANGELOG.md                 # Version history and changes
├── API_README.md                # API usage documentation
├── deployment/                  # Deployment configurations
│   ├── docker-compose.yml       # Container orchestration
│   ├── Dockerfile               # Application container
│   ├── Dockerfile.worker        # Worker container
│   └── cloudformation-*.yml     # AWS infrastructure
├── storage/                     # Local storage directory
│   ├── uploads/                 # Uploaded files
│   ├── processing/              # Temporary processing files
│   └── results/                 # Generated outputs
│       ├── clips/               # Video clips
│       └── faceless-videos/     # Faceless videos
└── test/                        # Test files and utilities
```

## Data Flow

### Video Clip Generation Flow:
1. **Upload**: User uploads video via API
2. **Queue**: Job queued in Celery with unique processing_id
3. **Process**: Background worker processes video through AI pipeline
4. **Store**: Generated clips and captions stored in configured storage
5. **Notify**: Job status updated, user can download results

### Faceless Video Generation Flow:
1. **Input**: User provides story content, selects voice and style
2. **Generate**: AI creates story, breaks into scenes, generates images and audio
3. **Compose**: Video created from scenes without burned-in subtitles
4. **Output**: Final video and separate caption JSON file provided

## Storage Architecture

### Local Storage Structure:
```
storage/
├── uploads/
│   └── {processing_id}.mp4           # Original uploaded videos
├── processing/
│   └── temp_files/                   # Temporary processing files
└── results/
    ├── {processing_id}/              # Video clip results
    │   ├── clip_01_title.mp4
    │   ├── clip_01_title.json        # Word-level captions
    │   └── ...
    └── faceless-videos/
        └── {processing_id}/          # Faceless video results
            ├── faceless_video_{id}.mp4
            ├── faceless_video_{id}.json
            ├── scene_01.png
            ├── audio_01.mp3
            └── ...
```

### S3 Storage Structure:
```
s3://bucket-name/
├── uploads/
│   └── {processing_id}.mp4
├── processing/
│   └── temp_files/
└── results/
    ├── clips/
    │   └── {processing_id}/
    └── faceless-videos/
        └── {processing_id}/
```

## Database Schema

### Video Clip Tables:
```sql
-- Processing jobs for video clips
CREATE TABLE processing_jobs (
    id INTEGER PRIMARY KEY,
    processing_id TEXT UNIQUE,
    status TEXT,
    progress_percentage INTEGER,
    input_filename TEXT,
    original_filename TEXT,
    num_clips_requested INTEGER,
    aspect_ratio TEXT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

-- Generated clips
CREATE TABLE generated_clips (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES processing_jobs(id),
    clip_number INTEGER,
    clip_filename TEXT,
    caption_filename TEXT,
    duration_seconds REAL,
    file_size_bytes INTEGER,
    clip_text_preview TEXT
);
```

### Faceless Video Tables:
```sql
-- Faceless video generation jobs
CREATE TABLE faceless_video_jobs (
    id INTEGER PRIMARY KEY,
    processing_id TEXT UNIQUE,
    status TEXT,
    progress_percentage INTEGER,
    story_title TEXT,
    story_description TEXT,
    story_content TEXT,
    story_category TEXT,
    image_style TEXT,
    voice_id TEXT,
    aspect_ratio TEXT,
    generated_story TEXT,
    final_video_filename TEXT,
    caption_filename TEXT,
    total_scenes_generated INTEGER,
    total_duration_seconds REAL,
    file_size_bytes INTEGER,
    openai_cost REAL,
    replicate_cost REAL,
    total_cost REAL,
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

-- Individual scenes in faceless videos
CREATE TABLE faceless_video_scenes (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES faceless_video_jobs(id),
    scene_number INTEGER,
    scene_text TEXT,
    image_prompt TEXT,
    image_filename TEXT,
    audio_filename TEXT,
    image_url TEXT,
    start_time REAL,
    end_time REAL,
    duration REAL,
    image_generation_time REAL,
    audio_generation_time REAL
);
```

## Configuration Management

### Environment Variables:
- **Storage**: `STORAGE_TYPE`, S3 credentials, local paths
- **Database**: `DATABASE_URL`, connection settings
- **AI Services**: OpenAI API key, Replicate token
- **Processing**: Model settings, quality parameters
- **API**: Host, port, CORS settings
- **Workers**: Celery configuration, concurrency settings

### Feature Flags:
- Debug mode and detailed error reporting
- Cost tracking and budget limits
- Processing time limits and retry settings

## API Authentication & Security

### Current Implementation:
- CORS configuration for cross-origin requests
- File type and size validation
- Input sanitization and validation
- Rate limiting capabilities (configurable)

### Ready for Enhancement:
- API key authentication
- User account management
- Usage quotas and billing
- Admin panel access

## Monitoring & Observability

### Logging:
- Structured logging with configurable levels
- Processing progress tracking
- Error reporting with stack traces
- Cost tracking for AI services

### Health Checks:
- Database connectivity
- Redis/Celery status
- Storage availability (Local/S3)
- AI service availability

### Metrics Ready:
- Processing times and success rates
- Storage usage and costs
- AI service usage and costs
- User activity and patterns

## Deployment Options

### Docker Compose (Recommended for Development):
```yaml
services:
  api:          # FastAPI application
  worker:       # Celery worker
  redis:        # Message broker
  postgres:     # Database (optional)
```

### AWS CloudFormation (Production):
- ECS/Fargate services
- Application Load Balancer
- RDS database
- ElastiCache Redis
- S3 storage
- Auto-scaling configuration

### Kubernetes (Enterprise):
- Multi-pod deployment
- Horizontal scaling
- Resource management
- Service mesh ready

## Scalability Considerations

### Horizontal Scaling:
- Stateless API design
- Celery worker scaling
- Database connection pooling
- Storage service integration

### Performance Optimization:
- Async processing with progress tracking
- Memory management and cleanup
- GPU acceleration support
- Batch processing capabilities

### Resource Management:
- Configurable worker concurrency
- Memory usage monitoring
- Temporary file cleanup
- Storage quota management

## Future Enhancements

### Planned Features:
1. **Web UI**: React-based frontend for easier usage
2. **Webhooks**: Real-time notifications for job completion
3. **Batch Processing**: Multiple video processing
4. **Advanced AI**: Custom model fine-tuning
5. **Analytics**: Usage analytics and reporting
6. **Mobile API**: Mobile-optimized endpoints

### Faceless Video Enhancements:
1. **Custom Voices**: Voice cloning capabilities
2. **Video Templates**: Pre-designed video styles
3. **Music Integration**: Background music and sound effects
4. **Advanced Editing**: Transitions and effects
5. **Brand Customization**: Logos and brand elements

## Cost Optimization

### AI Service Costs:
- **Faceless Videos**: $0.20-$1.50 per video
  - Story generation: ~$0.03
  - Image generation: ~$0.70 (14 images)
  - TTS generation: ~$0.05
- **Video Processing**: Minimal cost (local processing)

### Storage Costs:
- S3 storage and bandwidth charges
- Local storage space requirements
- Temporary file cleanup automation

### Optimization Strategies:
- Efficient prompt engineering
- Image generation batching
- Storage lifecycle policies
- Resource usage monitoring

## Created Files Registry

### Core Application Files:
- `main.py` - API endpoints and application setup
- `tasks.py` - Background processing tasks
- `clip_generator.py` - Video clip processing logic
- `faceless_video_generator.py` - Faceless video generation
- `models.py` - Database models and schemas
- `storage_handler.py` - Storage abstraction layer
- `config.py` - Configuration management

### Endpoints Registry:

#### Video Clip Endpoints:
- `POST /api/upload-video` - Video upload and processing
- `GET /api/status/{processing_id}` - Processing status
- `GET /api/download/clips/{processing_id}/{filename}` - Clip download
- `GET /api/download/captions/{processing_id}/{filename}` - Caption download

#### Faceless Video Endpoints:
- `POST /api/faceless-video/generate` - Generate faceless video
- `GET /api/faceless-video/status/{processing_id}` - Generation status
- `GET /api/download/faceless-video/{processing_id}` - Video download
- `GET /api/download/faceless-captions/{processing_id}` - Caption download
- `GET /api/faceless-video/options` - Available options

#### Utility Endpoints:
- `GET /api/health` - System health check
- `GET /api/jobs` - List processing jobs (admin)
- `DELETE /api/jobs/{processing_id}` - Delete job and files

### Background Tasks:
- `process_video_task` - Video clip generation
- `generate_faceless_video_task` - Faceless video generation

### Database Models:
- `ProcessingJob` - Video processing job tracking
- `GeneratedClip` - Generated clip information
- `FacelessVideoJob` - Faceless video job tracking
- `FacelessVideoScene` - Individual scene information

---

This architecture provides a robust, scalable foundation for both video clip generation and faceless video creation, with clear separation of concerns and comprehensive feature coverage. 