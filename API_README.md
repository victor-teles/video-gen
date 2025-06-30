# 🎬 Video Clip Generator API

**AI-powered video clip generation with YOLO auto-cropping and real-time progress tracking**

This FastAPI application provides a complete backend system for automatically generating optimized video clips from longer videos using ClipsAI, WhisperX, and YOLO detection.

## ✨ Features

- **🚀 Async File Upload**: Upload videos up to 500MB
- **🔄 Real-time Progress**: Track processing with live progress updates  
- **🎯 Smart Cropping**: YOLO-based auto-cropping for optimal framing
- **📝 Word-level Captions**: JSON captions with precise timestamps
- **⚡ Queue System**: Redis + Celery for background processing
- **💾 Database Tracking**: SQLAlchemy with job history
- **📱 Multiple Formats**: Support for 9:16, 1:1, 16:9 ratios
- **🔍 RESTful API**: Full OpenAPI documentation

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Celery Worker  │    │   Redis Queue   │
│   (Web Server)  │◄──►│  (Processing)    │◄──►│   (Message)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
          │                       │                       
          ▼                       ▼                       
┌─────────────────┐    ┌──────────────────┐              
│   SQLAlchemy    │    │   File Storage   │              
│   (Database)    │    │   (Uploads/Results)│            
└─────────────────┘    └──────────────────┘              
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **Redis Server** 
- **FFmpeg** (for video processing)

### 1. Installation

```bash
# Clone or navigate to the project
cd trodai_api

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup Redis

**Windows:**
```bash
# Download and install Redis from https://redis.io/download
# Or use Docker:
docker run -d -p 6379:6379 redis:alpine
```

**Linux/Mac:**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis
```

### 3. Start the API

**Option A: Automated Startup (Recommended)**
```bash
python start_api.py
```

**Option B: Manual Startup**
```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Celery Worker
celery -A tasks.celery_app worker --loglevel=info

# Terminal 3: Start FastAPI
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Access the API

- **API Server**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📡 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload-video` | Upload video and start processing |
| `GET` | `/api/status/{processing_id}` | Get processing status and progress |
| `GET` | `/api/download/clips/{processing_id}/{filename}` | Download generated clip |
| `GET` | `/api/download/captions/{processing_id}/{filename}` | Download caption JSON |

### Management Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check (Redis, Database, Workers) |
| `GET` | `/api/jobs` | List all processing jobs |
| `DELETE` | `/api/jobs/{processing_id}` | Delete job and files |

## 🎯 Usage Examples

### Upload Video for Processing

```bash
curl -X POST "http://localhost:8000/api/upload-video" \
  -F "file=@your_video.mp4" \
  -F "num_clips=3" \
  -F "ratio=9:16"
```

**Response:**
```json
{
  "processing_id": "12345678-1234-1234-1234-123456789012",
  "status": "queued",
  "message": "Video uploaded successfully and processing started",
  "original_filename": "your_video.mp4",
  "num_clips_requested": 3,
  "aspect_ratio": "9:16",
  "estimated_time": "5-15 minutes",
  "task_id": "celery-task-id"
}
```

### Check Processing Status

```bash
curl "http://localhost:8000/api/status/12345678-1234-1234-1234-123456789012"
```

**Response (Processing):**
```json
{
  "processing_id": "12345678-1234-1234-1234-123456789012",
  "status": "processing",
  "progress": 65,
  "current_step": "Clip 2/3: Auto-cropping with YOLO...",
  "created_at": "2024-01-01T10:00:00.000Z",
  "started_at": "2024-01-01T10:01:00.000Z",
  "estimated_remaining": "3 minutes",
  "total_clips": 0,
  "input_filename": "your_video.mp4",
  "num_clips_requested": 3,
  "aspect_ratio": "9:16"
}
```

**Response (Completed):**
```json
{
  "processing_id": "12345678-1234-1234-1234-123456789012",
  "status": "completed",
  "progress": 100,
  "current_step": "Completed! Generated 3 clips",
  "created_at": "2024-01-01T10:00:00.000Z",
  "started_at": "2024-01-01T10:01:00.000Z",
  "completed_at": "2024-01-01T10:15:00.000Z",
  "total_clips": 3,
  "processing_time": 840,
  "clips": [
    {
      "clip_id": 1,
      "filename": "clip_01_talking_about_ai_revolution.mp4",
      "duration": 94.9,
      "preview_text": "So today we're talking about the AI revolution",
      "file_size": "45.2MB",
      "start_time": 120.5,
      "end_time": 215.4,
      "download_url": "/api/download/clips/12345.../clip_01_talking_about_ai_revolution.mp4",
      "captions_url": "/api/download/captions/12345.../clip_01_talking_about_ai_revolution.json"
    }
  ]
}
```

### Download Files

```bash
# Download video clip
curl -O "http://localhost:8000/api/download/clips/12345.../clip_01_talking_about_ai_revolution.mp4"

# Download captions
curl -O "http://localhost:8000/api/download/captions/12345.../clip_01_talking_about_ai_revolution.json"
```

## 📊 Processing Pipeline

1. **Upload & Validation** (0-5%)
   - File type and size validation
   - Secure file storage
   - Database job creation

2. **Transcription** (5-30%)
   - WhisperX audio transcription
   - Word-level timestamp extraction

3. **Clip Detection** (30-50%)
   - ClipsAI content analysis
   - Quality ranking and filtering
   - Duration filtering (30-120 seconds)

4. **Clip Processing** (50-100%)
   - High-quality video extraction
   - YOLO-based auto-cropping
   - Caption JSON generation
   - File optimization

## 🗂️ File Structure

```
trodai_api/
├── main.py              # FastAPI application
├── tasks.py             # Celery background tasks
├── models.py            # Database models
├── database.py          # Database connection
├── config.py            # Configuration settings
├── clip_generator.py    # Core clip processing logic
├── start_api.py         # Automated startup script
├── requirements.txt     # Python dependencies
├── API_README.md        # This documentation
└── storage/             # File storage (auto-created)
    ├── uploads/         # Uploaded videos
    ├── processing/      # Temporary files
    └── results/         # Generated clips
```

## ⚙️ Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=sqlite:///./clip_generator.db

# Redis
REDIS_URL=redis://localhost:6379/0

# File Limits
MAX_FILE_SIZE=524288000  # 500MB
MAX_CLIPS_PER_REQUEST=10
```

### Default Settings

- **Upload limit**: 500MB
- **Supported formats**: MP4, AVI, MOV, MKV, WEBM
- **Clip duration**: 30-120 seconds
- **Default aspect ratio**: 9:16
- **File cleanup**: Uploads (24h), Results (72h)

## 🔧 Development

### Running Tests

```bash
# Test dependencies
python test_dependencies.py

# Test API endpoints
curl http://localhost:8000/api/health
```

### Database Management

```bash
# View database
sqlite3 clip_generator.db

# Clear all jobs
DELETE FROM processing_jobs;
```

### Monitoring

```bash
# Check Celery workers
celery -A tasks.celery_app inspect active

# Monitor Redis
redis-cli monitor
```

## 🚨 Troubleshooting

### Common Issues

**1. Redis Connection Error**
```
Solution: Ensure Redis is running on port 6379
Command: redis-server
```

**2. Celery Worker Not Starting**
```
Solution: Check Python path and dependencies
Command: celery -A tasks.celery_app worker --loglevel=debug
```

**3. YOLO Model Download**
```
Issue: First run downloads YOLOv8 model (~6MB)
Solution: Wait for download to complete
```

**4. FFmpeg Not Found**
```
Solution: Install FFmpeg and add to PATH
Windows: https://ffmpeg.org/download.html#build-windows
Linux: sudo apt install ffmpeg
Mac: brew install ffmpeg
```

### Debug Mode

```bash
# Start with debug logging
uvicorn main:app --log-level debug
celery -A tasks.celery_app worker --loglevel=debug
```

## 📈 Performance Optimization

### For Production

1. **Use PostgreSQL** instead of SQLite
2. **Multiple Celery workers** for parallel processing
3. **Redis Cluster** for high availability
4. **File CDN** for clip distribution
5. **Load balancer** for FastAPI instances

### Scaling Configuration

```python
# config.py adjustments for production
DATABASE_URL = "postgresql://user:pass@localhost/clipgen"
REDIS_URL = "redis://redis-cluster:6379/0"
```

## 🛡️ Security Considerations

- File type validation prevents malicious uploads
- Unique processing IDs prevent unauthorized access
- File cleanup prevents storage bloat
- CORS configuration for web integration

## 📚 Additional Resources

- **ClipsAI Documentation**: https://clipsai.com/docs
- **WhisperX GitHub**: https://github.com/m-bain/whisperX
- **FastAPI Documentation**: https://fastapi.tiangolo.com
- **Celery Documentation**: https://docs.celeryproject.org

---

**🎬 Ready to generate some amazing clips? Start with `python start_api.py` and visit http://localhost:8000/docs!** 