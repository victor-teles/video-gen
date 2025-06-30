"""
Configuration settings for the Video Clip Generator API
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Storage configuration - Clean up any comments or whitespace
storage_type_raw = os.getenv("STORAGE_TYPE", "s3")
STORAGE_TYPE = storage_type_raw.split('#')[0].strip() if storage_type_raw else "s3"

# S3 Configuration
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "trod-video-clips")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Base directories (used for local storage or temporary files when using S3)
BASE_DIR = Path(__file__).parent
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", BASE_DIR / "storage"))
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", STORAGE_DIR / "uploads"))
PROCESSING_DIR = Path(os.getenv("PROCESSING_DIR", STORAGE_DIR / "processing"))
RESULTS_DIR = Path(os.getenv("RESULTS_DIR", STORAGE_DIR / "results"))

# Create local directories if they don't exist (needed even with S3 for temporary storage)
for directory in [STORAGE_DIR, UPLOADS_DIR, PROCESSING_DIR, RESULTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./clip_generator.db")

# Redis/Celery
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# File upload settings
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 500 * 1024 * 1024))  # 500MB default
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

# Processing settings
DEFAULT_NUM_CLIPS = int(os.getenv("DEFAULT_NUM_CLIPS", 3))
DEFAULT_RATIO = os.getenv("DEFAULT_RATIO", "9:16")
MAX_CLIPS_PER_REQUEST = int(os.getenv("MAX_CLIPS_PER_REQUEST", 10))
MIN_CLIP_DURATION = int(os.getenv("MIN_CLIP_DURATION", 30))
MAX_CLIP_DURATION = int(os.getenv("MAX_CLIP_DURATION", 120))

# API settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
API_TITLE = os.getenv("API_TITLE", "Video Clip Generator API")
API_VERSION = os.getenv("API_VERSION", "1.0.0")
API_DESCRIPTION = os.getenv("API_DESCRIPTION", "AI-powered video clip generation with YOLO auto-cropping")

# Security settings
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
RATE_LIMIT = int(os.getenv("RATE_LIMIT", 60))

# File cleanup (hours)
CLEANUP_UPLOADS_AFTER = int(os.getenv("CLEANUP_UPLOADS_AFTER", 24))
CLEANUP_RESULTS_AFTER = int(os.getenv("CLEANUP_RESULTS_AFTER", 72))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", None)

# Celery worker settings
CELERY_WORKER_CONCURRENCY = int(os.getenv("CELERY_WORKER_CONCURRENCY", 1))
CELERY_LOG_LEVEL = os.getenv("CELERY_LOG_LEVEL", "INFO")
CELERY_TASK_TIME_LIMIT = int(os.getenv("CELERY_TASK_TIME_LIMIT", 3600))

# FFmpeg settings
FFMPEG_PATH = os.getenv("FFMPEG_PATH", None)  # Auto-detect if None
VIDEO_CRF = int(os.getenv("VIDEO_CRF", 18))
AUDIO_BITRATE = os.getenv("AUDIO_BITRATE", "192k")

# AI Model settings
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
YOLO_MODEL = os.getenv("YOLO_MODEL", "yolov8n.pt")
AI_DEVICE = os.getenv("AI_DEVICE", "auto")

# Development settings
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
AUTO_RELOAD = os.getenv("AUTO_RELOAD", "True").lower() == "true"
SHOW_ERROR_DETAILS = os.getenv("SHOW_ERROR_DETAILS", "False").lower() == "true" 