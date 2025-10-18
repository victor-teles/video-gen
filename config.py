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
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "https://s3.us-east-1.amazonaws.com")
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

# ============================================================================
# CLIP SELECTION AI CONFIGURATION (OpenRouter)
# ============================================================================

# OpenRouter API settings
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Primary model and fallback chain
CLIP_SELECTION_MODEL = os.getenv("CLIP_SELECTION_MODEL", "tngtech/deepseek-r1t2-chimera:free")
CLIP_SELECTION_FALLBACK_MODELS_STR = os.getenv(
    "CLIP_SELECTION_FALLBACK_MODELS",
    "deepseek/deepseek-chat-v3.1:free,qwen/qwen3-235b-a22b:free,baidu/ernie-4.5-21b-a3b-thinking,google/gemini-2.5-flash-preview-09-2025,x-ai/grok-4-fast"
)
CLIP_SELECTION_FALLBACK_MODELS = [m.strip() for m in CLIP_SELECTION_FALLBACK_MODELS_STR.split(',')]

# All available models in priority order
CLIP_SELECTION_ALL_MODELS = [CLIP_SELECTION_MODEL] + CLIP_SELECTION_FALLBACK_MODELS

# Model configuration
CLIP_SELECTION_TEMPERATURE = float(os.getenv("CLIP_SELECTION_TEMPERATURE", "0.3"))
CLIP_SELECTION_MAX_TOKENS = int(os.getenv("CLIP_SELECTION_MAX_TOKENS", "1000"))
CLIP_SELECTION_MAX_RETRIES = int(os.getenv("CLIP_SELECTION_MAX_RETRIES", "3"))

# Feature flags
ENABLE_AI_CLIP_SELECTION = os.getenv("ENABLE_AI_CLIP_SELECTION", "true").lower() == "true"

# Cost tracking (free models = $0)
OPENROUTER_COST_PER_TOKEN = float(os.getenv("OPENROUTER_COST_PER_TOKEN", "0.0"))

# ============================================================================
# FACELESS VIDEO GENERATION SETTINGS
# ============================================================================

# API Keys for Faceless Video Generation
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
FAL_KEY = os.getenv("FAL_KEY")  # Optional alternative

# Story Generation Settings
STORY_MODEL = os.getenv("STORY_MODEL", "gpt-4")
STORY_TEMPERATURE = float(os.getenv("STORY_TEMPERATURE", "0.9"))
STORY_CHAR_LIMIT_MIN = int(os.getenv("STORY_CHAR_LIMIT_MIN", "700"))
STORY_CHAR_LIMIT_MAX = int(os.getenv("STORY_CHAR_LIMIT_MAX", "800"))
MAX_SCENES = int(os.getenv("MAX_SCENES", "14"))

# Image Generation Settings
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "black-forest-labs/flux-schnell")
IMAGE_ASPECT_RATIO = os.getenv("IMAGE_ASPECT_RATIO", "9:16")
IMAGE_INFERENCE_STEPS = int(os.getenv("IMAGE_INFERENCE_STEPS", "4"))
IMAGE_GUIDANCE = float(os.getenv("IMAGE_GUIDANCE", "3.0"))
IMAGE_QUALITY = int(os.getenv("IMAGE_QUALITY", "100"))

# TTS Settings
TTS_MODEL = os.getenv("TTS_MODEL", "tts-1")
TTS_SPEECH_RATE = float(os.getenv("TTS_SPEECH_RATE", "1.1"))

# Available Options (following SmartClipAI patterns)
STORY_CATEGORIES = [
    "custom", "scary", "mystery", "bedtime", "history", 
    "urban_legends", "motivational", "fun_facts", 
    "life_tips", "philosophy", "love"
]

AVAILABLE_VOICES = [
    "alloy", "echo", "fable", "onyx", "nova", "shimmer"
]

IMAGE_STYLES = [
    "photorealistic", "cinematic", "anime", "comic-book", "pixar-art"
]

# Cost Estimation (per unit)
OPENAI_COST_PER_TOKEN = float(os.getenv("OPENAI_COST_PER_TOKEN", "0.00003"))  # GPT-4 input
OPENAI_TTS_COST_PER_CHAR = float(os.getenv("OPENAI_TTS_COST_PER_CHAR", "0.000015"))  # TTS
REPLICATE_COST_PER_IMAGE = float(os.getenv("REPLICATE_COST_PER_IMAGE", "0.05"))  # Flux

# Faceless Video Limits
MAX_FACELESS_VIDEOS_PER_USER = int(os.getenv("MAX_FACELESS_VIDEOS_PER_USER", "10"))  # Per day
MAX_STORY_TITLE_LENGTH = int(os.getenv("MAX_STORY_TITLE_LENGTH", "100"))  # Characters
MAX_STORY_DESCRIPTION_LENGTH = int(os.getenv("MAX_STORY_DESCRIPTION_LENGTH", "500"))  # Characters
MAX_STORY_CONTENT_LENGTH = int(os.getenv("MAX_STORY_CONTENT_LENGTH", "2000"))  # Characters

# Faceless Video Storage Paths (following existing patterns)
FACELESS_VIDEOS_DIR = Path(os.getenv("FACELESS_VIDEOS_DIR", RESULTS_DIR / "faceless-videos"))
FACELESS_VIDEOS_DIR.mkdir(parents=True, exist_ok=True) 