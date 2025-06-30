# 🚀 Video Clip Generator Deployment

This directory contains scripts and documentation for deploying the Video Clip Generator.

## 📦 S3 Storage Setup

The application uses AWS S3 for storing:
- 📤 Uploaded videos (`uploads/`)
- ⚙️ Processing files (`processing/`)
- 📥 Generated clips and captions (`results/`)

### 🔧 Setup Steps

1. **Create `.env` file in project root:**
   ```env
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_REGION=us-east-1
   S3_BUCKET_NAME=trod-video-clips
   ```

2. **Run S3 setup script:**
   ```bash
   cd deployment
   chmod +x s3_setup.sh
   ./s3_setup.sh
   ```

### 📁 S3 Bucket Structure

```
s3://trod-video-clips/
├── uploads/
│   └── {processing_id}/
│       └── original.mp4
├── processing/
│   └── {processing_id}/
│       ├── temp_clips/
│       └── transcriptions/
└── results/
    └── {processing_id}/
        ├── clip_01_title.mp4
        ├── clip_01_title.json
        ├── clip_02_title.mp4
        └── clip_02_title.json
```

### ⚙️ Lifecycle Rules

- `uploads/`: Files deleted after 1 day
- `processing/`: Files deleted after 1 day
- `results/`: Files deleted after 7 days

### 🔒 Security

- CORS configured for:
  - `https://trod.ai`
  - `https://api.trod.ai`
  - `http://localhost:3000` (development)
  - `http://localhost:8000` (development)

### 📝 Usage in Code

```python
from deployment.s3_storage import S3Storage

# Initialize storage
s3 = S3Storage()

# Upload file
s3.upload_file('local/path/video.mp4', 'uploads/123/video.mp4')

# Download file
s3.download_file('results/123/clip_01.mp4', 'local/path/clip.mp4')

# Get presigned URL
url = s3.get_presigned_url('results/123/clip_01.mp4')

# List files
files = s3.list_files('results/123/')

# Delete file
s3.delete_file('uploads/123/video.mp4')

# Move file
s3.move_file('processing/123/temp.mp4', 'results/123/final.mp4')
``` 