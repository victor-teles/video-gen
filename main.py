"""
FastAPI application for Video Clip Generator
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pathlib import Path
import uuid
import aiofiles
import mimetypes
from typing import List, Optional
import boto3
from botocore.exceptions import ClientError
import tempfile
import os

import config
from database import get_db, init_database
from models import ProcessingJob, GeneratedClip
from tasks import process_video_task, celery_app
from storage_handler import StorageHandler

# Initialize FastAPI app
app = FastAPI(
    title=config.API_TITLE,
    version=config.API_VERSION,
    description=config.API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def check_s3_connection():
    """Check S3 connectivity and bucket setup"""
    try:
        print(f"🔍 Debug: Raw STORAGE_TYPE value: '{config.STORAGE_TYPE}'")
        
        storage_type = config.STORAGE_TYPE.split('#')[0].strip()
        print(f"🔍 Debug: Cleaned STORAGE_TYPE value: '{storage_type}'")
        
        if storage_type != 's3':
            print("ℹ️  Using local storage (S3 not configured)")
            return True
            
        print("🔄 Checking S3 configuration...")
        
        # Check if AWS credentials are set
        if not all([config.AWS_ACCESS_KEY_ID, config.AWS_SECRET_ACCESS_KEY, config.AWS_REGION]):
            print("❌ AWS credentials not configured in .env file")
            return False
            
        # Initialize S3 client
        s3 = boto3.client('s3',
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            region_name=config.AWS_REGION
        )
        
        # Check if bucket exists and is accessible
        try:
            s3.head_bucket(Bucket=config.S3_BUCKET_NAME)
            print(f"✅ Connected to S3 bucket: {config.S3_BUCKET_NAME}")
            
            # Check required folders
            required_folders = ['uploads/', 'processing/', 'results/']
            existing_folders = set()
            
            response = s3.list_objects_v2(
                Bucket=config.S3_BUCKET_NAME,
                Delimiter='/'
            )
            
            if 'CommonPrefixes' in response:
                existing_folders = {p['Prefix'] for p in response['CommonPrefixes']}
            
            missing_folders = [f for f in required_folders if f not in existing_folders]
            
            if missing_folders:
                print("⚠️  Creating missing S3 folders:")
                for folder in missing_folders:
                    s3.put_object(Bucket=config.S3_BUCKET_NAME, Key=folder)
                    print(f"   ✅ Created: {folder}")
            
            # Verify bucket configuration
            try:
                versioning = s3.get_bucket_versioning(Bucket=config.S3_BUCKET_NAME)
                if versioning.get('Status') == 'Enabled':
                    print("✅ Bucket versioning: Enabled")
                else:
                    print("⚠️  Bucket versioning: Not enabled")
                
                lifecycle = s3.get_bucket_lifecycle_configuration(Bucket=config.S3_BUCKET_NAME)
                if lifecycle.get('Rules'):
                    print("✅ Lifecycle policies: Configured")
                    
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchLifecycleConfiguration':
                    print("⚠️  Lifecycle policies: Not configured")
                else:
                    raise e
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                print(f"❌ S3 bucket '{config.S3_BUCKET_NAME}' does not exist")
            elif error_code == 'AccessDenied':
                print(f"❌ Access denied to S3 bucket '{config.S3_BUCKET_NAME}'")
            else:
                print(f"❌ S3 error: {str(e)}")
            return False
            
    except ImportError:
        print("❌ AWS SDK (boto3) not installed")
        return False
    except Exception as e:
        print(f"❌ S3 configuration error: {str(e)}")
        return False

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    print("=" * 50)
    print(f"🚀 Starting {config.API_TITLE} v{config.API_VERSION}")
    print("=" * 50)
    
    print("🗄️  Initializing database...")
    init_database()
    print("✅ Database initialized successfully")
    
    # Check S3 configuration
    s3_ok = await check_s3_connection()
    if not s3_ok and config.STORAGE_TYPE == 's3':
        print("\n⚠️  Warning: S3 storage is not properly configured")
        print("   Please run 's3_setup.bat' to configure S3 storage")
        print("   Or set STORAGE_TYPE=local in .env to use local storage")
    
    print("\n📋 Service Status:")
    print("   ✅ Database: Connected")
    
    # Use cleaned storage type for consistent checking
    storage_type = config.STORAGE_TYPE.split('#')[0].strip()
    if storage_type == 's3':
        print(f"   ✅ S3 Storage: Connected to {config.S3_BUCKET_NAME}")
    else:
        print("   ✅ Local Storage: Enabled")
    print("✅ Application startup complete")
    print("=" * 50)

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    print("🛑 Shutting down application...")

# Utility functions
def validate_file_type(filename: str) -> bool:
    """Validate if file type is allowed"""
    file_ext = Path(filename).suffix.lower()
    return file_ext in config.ALLOWED_VIDEO_EXTENSIONS

def validate_file_size(file_size: int) -> bool:
    """Validate if file size is within limits"""
    return file_size <= config.MAX_FILE_SIZE

def parse_aspect_ratio(ratio: str) -> tuple:
    """Parse and validate aspect ratio"""
    try:
        parts = ratio.split(':')
        if len(parts) != 2:
            raise ValueError("Invalid format")
        return (int(parts[0]), int(parts[1]))
    except:
        raise HTTPException(status_code=400, detail=f"Invalid aspect ratio format: {ratio}")

# API Routes

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": f"Welcome to {config.API_TITLE}",
        "version": config.API_VERSION,
        "docs": "/docs",
        "status": "running"
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Celery connection
        inspector = celery_app.control.inspect()
        active_workers = inspector.active()
        
        return {
            "status": "healthy",
            "database": "connected",
            "celery_workers": len(active_workers) if active_workers else 0,
            "storage_available": True
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )

@app.post("/api/upload-video")
async def upload_video(
    file: UploadFile = File(...),
    num_clips: int = config.DEFAULT_NUM_CLIPS,
    ratio: str = config.DEFAULT_RATIO,
    db: Session = Depends(get_db)
):
    """
    Upload video and start processing
    
    - **file**: Video file to process
    - **num_clips**: Number of clips to generate (1-10)
    - **ratio**: Aspect ratio (e.g., "9:16", "1:1", "16:9")
    """
    
    # Validate input parameters
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not validate_file_type(file.filename):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(config.ALLOWED_VIDEO_EXTENSIONS)}"
        )
    
    if num_clips < 1 or num_clips > config.MAX_CLIPS_PER_REQUEST:
        raise HTTPException(
            status_code=400, 
            detail=f"num_clips must be between 1 and {config.MAX_CLIPS_PER_REQUEST}"
        )
    
    # Validate aspect ratio
    parse_aspect_ratio(ratio)
    
    temp_file = None
    try:
        # Generate unique processing ID and filename
        processing_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix
        unique_filename = f"{processing_id}{file_extension}"
        
        # Initialize storage handler
        storage = StorageHandler()
        
        # Read and validate file size
        file_content = await file.read()
        if not validate_file_size(len(file_content)):
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size: {config.MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
        temp_file.write(file_content)
        temp_file.close()  # Close the file before further operations
        
        # Define the destination path
        storage_type = config.STORAGE_TYPE.split('#')[0].strip()
        if storage_type == 's3':
            dest_path = f"uploads/{unique_filename}"
        else:
            dest_path = config.UPLOADS_DIR / unique_filename
            os.makedirs(config.UPLOADS_DIR, exist_ok=True)
        
        # Save file using storage handler
        if not storage.save_file(temp_file.name, dest_path):
            raise HTTPException(status_code=500, detail="Failed to save file to storage")
        
        # Create database record
        job = ProcessingJob(
            processing_id=processing_id,
            input_filename=unique_filename,
            original_filename=file.filename,
            num_clips_requested=num_clips,
            aspect_ratio=ratio,
            status="pending"
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Queue processing task
        task = process_video_task.delay(job.id)
        
        print(f"📤 Video uploaded and queued: {file.filename} -> {processing_id}")
        if storage_type == 's3':
            print(f"   📦 Saved to S3: s3://{config.S3_BUCKET_NAME}/uploads/{unique_filename}")
        
        return {
            "processing_id": processing_id,
            "status": "queued",
            "message": "Video uploaded successfully and processing started",
            "original_filename": file.filename,
            "num_clips_requested": num_clips,
            "aspect_ratio": ratio,
            "estimated_time": "5-15 minutes",
            "task_id": task.id
        }
        
    except Exception as e:
        # Clean up temporary file if it exists
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except Exception as cleanup_error:
                print(f"Warning: Failed to clean up temporary file: {cleanup_error}")
        
        raise HTTPException(status_code=500, detail=f"Failed to process upload: {str(e)}")
    
    finally:
        # Ensure temporary file is cleaned up
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except Exception as cleanup_error:
                print(f"Warning: Failed to clean up temporary file in finally block: {cleanup_error}")

@app.get("/api/status/{processing_id}")
async def get_status(processing_id: str, db: Session = Depends(get_db)):
    """
    Get processing status and progress
    
    - **processing_id**: The processing ID returned from upload
    """
    
    job = db.query(ProcessingJob).filter(ProcessingJob.processing_id == processing_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Processing job not found")
    
    # Base response
    response = job.to_dict()
    
    # Add clips information if completed
    if job.status == "completed":
        clips = db.query(GeneratedClip).filter(GeneratedClip.job_id == job.id).all()
        response["clips"] = [clip.to_dict() for clip in clips]
    
    # Add estimated remaining time
    if job.status == "processing" and job.progress_percentage > 0:
        # Rough estimation based on progress
        if job.progress_percentage < 100:
            estimated_remaining = max(1, int((100 - job.progress_percentage) / 10))
            response["estimated_remaining"] = f"{estimated_remaining} minutes"
    
    return response

@app.get("/api/download/clips/{processing_id}/{filename}")
async def download_clip(processing_id: str, filename: str, db: Session = Depends(get_db)):
    """
    Download generated video clip
    
    - **processing_id**: The processing ID
    - **filename**: The clip filename
    """
    
    # Verify job exists
    job = db.query(ProcessingJob).filter(ProcessingJob.processing_id == processing_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Processing job not found")
    
    # Verify job is completed
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    # Find the clip
    clip = db.query(GeneratedClip).filter(
        GeneratedClip.job_id == job.id,
        GeneratedClip.clip_filename == filename
    ).first()
    
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    
    file_path = config.RESULTS_DIR / processing_id / filename
    storage = StorageHandler()
    
    if config.STORAGE_TYPE == 's3':
        # For S3, generate a presigned URL and redirect
        url = storage.get_file_url(file_path, expires_in=3600)
        if not url:
            raise HTTPException(status_code=404, detail="File not found in storage")
        return RedirectResponse(url=url)
    else:
        # For local storage, serve the file directly
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        # Determine media type
        media_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

@app.get("/api/download/captions/{processing_id}/{filename}")
async def download_captions(processing_id: str, filename: str, db: Session = Depends(get_db)):
    """
    Download caption file
    
    - **processing_id**: The processing ID
    - **filename**: The caption filename
    """
    
    # Verify job exists
    job = db.query(ProcessingJob).filter(ProcessingJob.processing_id == processing_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Processing job not found")
    
    # Verify job is completed
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    # Find the clip with this caption
    clip = db.query(GeneratedClip).filter(
        GeneratedClip.job_id == job.id,
        GeneratedClip.caption_filename == filename
    ).first()
    
    if not clip:
        raise HTTPException(status_code=404, detail="Caption file not found")
    
    file_path = config.RESULTS_DIR / processing_id / filename
    storage = StorageHandler()
    
    if config.STORAGE_TYPE == 's3':
        # For S3, generate a presigned URL and redirect
        url = storage.get_file_url(file_path, expires_in=3600)
        if not url:
            raise HTTPException(status_code=404, detail="File not found in storage")
        return RedirectResponse(url=url)
    else:
        # For local storage, serve the file directly
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        return FileResponse(
            path=str(file_path),
            media_type="application/json",
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

@app.get("/api/jobs")
async def list_jobs(
    limit: int = 10, 
    offset: int = 0,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List processing jobs (for admin/debugging)
    
    - **limit**: Number of jobs to return
    - **offset**: Offset for pagination
    - **status**: Filter by status (pending, processing, completed, failed)
    """
    
    query = db.query(ProcessingJob)
    
    if status:
        query = query.filter(ProcessingJob.status == status)
    
    jobs = query.order_by(ProcessingJob.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "jobs": [job.to_dict() for job in jobs],
        "total": query.count(),
        "limit": limit,
        "offset": offset
    }

@app.delete("/api/jobs/{processing_id}")
async def delete_job(processing_id: str, db: Session = Depends(get_db)):
    """
    Delete a processing job and its files
    
    - **processing_id**: The processing ID to delete
    """
    
    job = db.query(ProcessingJob).filter(ProcessingJob.processing_id == processing_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Processing job not found")
    
    try:
        # Delete files
        upload_file = config.UPLOADS_DIR / job.input_filename
        if upload_file.exists():
            upload_file.unlink()
        
        results_dir = config.RESULTS_DIR / processing_id
        if results_dir.exists():
            import shutil
            shutil.rmtree(results_dir)
        
        # Delete database records (clips will be deleted automatically due to cascade)
        db.delete(job)
        db.commit()
        
        return {"message": f"Job {processing_id} deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete job: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT) 