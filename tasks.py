"""
Celery tasks for background video processing
"""
from celery import Celery
from celery.signals import worker_ready
import os
import time
import traceback
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
import logging
import tempfile

import config
from database import SessionLocal
from models import ProcessingJob, GeneratedClip
from clip_generator import ClipGenerator
from storage_handler import StorageHandler

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "video_processor",
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_reject_on_worker_lost=True,
    task_acks_late=True,  # Only acknowledge tasks after they complete
    worker_prefetch_multiplier=1  # Prevent worker from prefetching multiple tasks
)

@contextmanager
def get_db_session():
    """Context manager for database sessions with retry logic"""
    session = SessionLocal()
    max_retries = 3
    retry_delay = 1  # seconds
    
    try:
        yield session
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        session.rollback()
        for attempt in range(max_retries):
            try:
                # Try to reconnect and retry the transaction
                session.rollback()
                session.close()
                session = SessionLocal()
                yield session
                break
            except SQLAlchemyError as retry_error:
                if attempt == max_retries - 1:  # Last attempt
                    logger.error(f"Failed to recover database session after {max_retries} attempts")
                    raise
                logger.warning(f"Retry attempt {attempt + 1} failed: {retry_error}")
                time.sleep(retry_delay * (attempt + 1))
    finally:
        session.close()

def update_job_progress(db: Session, job_id: int, progress: int, step: str):
    """Update job progress in database with retry logic"""
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
            if job:
                job.progress_percentage = progress
                job.current_step = step
                if progress >= 100:
                    job.status = "completed"
                    job.completed_at = datetime.utcnow()
                db.commit()
                print(f"📊 Progress: {progress}% - {step}")
                break
        except SQLAlchemyError as e:
            db.rollback()
            if attempt == max_retries - 1:  # Last attempt
                logger.error(f"Failed to update job progress after {max_retries} attempts: {e}")
                raise
            logger.warning(f"Progress update attempt {attempt + 1} failed: {e}")
            time.sleep(retry_delay * (attempt + 1))

def update_job_status(db: Session, job_id: int, status: str, error_message: str = None):
    """Update job status in database with retry logic"""
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
            if job:
                job.status = status
                if error_message:
                    job.error_message = error_message
                if status == "processing":
                    job.started_at = datetime.utcnow()
                elif status in ["completed", "failed"]:
                    job.completed_at = datetime.utcnow()
                    if job.started_at:
                        processing_time = (job.completed_at - job.started_at).total_seconds()
                        job.processing_time_seconds = int(processing_time)
                db.commit()
                break
        except SQLAlchemyError as e:
            db.rollback()
            if attempt == max_retries - 1:  # Last attempt
                logger.error(f"Failed to update job status after {max_retries} attempts: {e}")
                raise
            logger.warning(f"Status update attempt {attempt + 1} failed: {e}")
            time.sleep(retry_delay * (attempt + 1))

class ProgressCallback:
    """Callback class for tracking clip generation progress"""
    
    def __init__(self, db: Session, job_id: int, total_clips: int):
        self.db = db
        self.job_id = job_id
        self.total_clips = total_clips
        self.base_progress = 50  # First 50% is transcription and finding clips
        self.current_clip = 0
    
    def update_transcription(self, step: str):
        """Update transcription progress"""
        progress = 10 if "starting" in step.lower() else 30
        update_job_progress(self.db, self.job_id, progress, step)
    
    def update_clip_finding(self, clips_found: int):
        """Update clip finding progress"""
        update_job_progress(self.db, self.job_id, 40, f"Found {clips_found} potential clips")
    
    def update_clip_selection(self, clips_selected: int):
        """Update clip selection progress"""
        update_job_progress(self.db, self.job_id, 50, f"Selected {clips_selected} clips for processing")
    
    def update_clip_processing(self, clip_number: int, step: str):
        """Update individual clip processing progress"""
        # Clips processing takes 50% of total progress (50-100%)
        clip_progress = (clip_number - 1) / self.total_clips * 50
        progress = int(50 + clip_progress)
        update_job_progress(self.db, self.job_id, progress, f"Clip {clip_number}/{self.total_clips}: {step}")
    
    def update_clip_completed(self, clip_number: int):
        """Update when a clip is completed"""
        clip_progress = clip_number / self.total_clips * 50
        progress = int(50 + clip_progress)
        update_job_progress(self.db, self.job_id, progress, f"Completed clip {clip_number}/{self.total_clips}")

@celery_app.task(bind=True, max_retries=3)
def process_video_task(self, job_id: int):
    """Process video task with improved error handling"""
    temp_input_file = None
    
    with get_db_session() as db:
        try:
            # Get job details
            job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
            if not job:
                logger.error(f"Job {job_id} not found")
                return
            
            # Update job status to processing
            update_job_status(db, job_id, "processing")
            
            # Initialize storage handler
            storage = StorageHandler()
            
            # Setup file paths based on storage type
            if config.STORAGE_TYPE.split('#')[0].strip() == 's3':
                # For S3, download file to temporary location
                temp_input_file = tempfile.NamedTemporaryFile(delete=False, suffix=Path(job.input_filename).suffix)
                temp_input_file.close()
                
                source_path = f"uploads/{job.input_filename}"
                logger.info(f"📥 Downloading file from S3: {source_path}")
                
                if not storage.get_file(source_path, temp_input_file.name):
                    raise FileNotFoundError(f"Failed to download file from S3: {source_path}")
                
                input_file = Path(temp_input_file.name)
                logger.info(f"✅ Downloaded file to: {input_file}")
            else:
                # For local storage, use direct path
                input_file = config.UPLOADS_DIR / job.input_filename
                if not input_file.exists():
                    raise FileNotFoundError(f"Input file not found: {input_file}")
            
            # Setup output directory
            output_dir = config.RESULTS_DIR / job.processing_id
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Parse aspect ratio
            try:
                ratio_parts = job.aspect_ratio.split(':')
                target_ratio = (int(ratio_parts[0]), int(ratio_parts[1]))
            except:
                raise ValueError(f"Invalid aspect ratio: {job.aspect_ratio}")
            
            # Create progress callback
            progress_callback = ProgressCallback(db, job_id, job.num_clips_requested)
            
            # Initialize clip generator
            generator = ClipGenerator(str(output_dir))
            
            # Step 1: Transcription
            progress_callback.update_transcription("Transcribing video...")
            generator._init_transcriber()  # Initialize transcriber before using it
            transcription = generator.transcriber.transcribe(audio_file_path=str(input_file))
            progress_callback.update_transcription("Transcription completed")
            
            # Clean up memory after transcription
            from clip_generator import cleanup_memory
            cleanup_memory()
            
            # Step 2: Find clips
            generator._init_clipfinder()  # Initialize clipfinder before using it
            clips = generator.clipfinder.find_clips(transcription=transcription)
            progress_callback.update_clip_finding(len(clips))
            
            # Clean up memory after clip finding
            cleanup_memory()
            
            if not clips:
                raise ValueError("No clips found in the video")
            
            # Step 3: Select clips
            clips_with_duration = []
            for clip in clips:
                duration = clip.end_time - clip.start_time
                if 30.0 <= duration <= 120.0:  # Filter clips between 30 and 120 seconds
                    clips_with_duration.append((clip, duration))
            
            # Sort by duration and take top N
            clips_with_duration.sort(key=lambda x: x[1], reverse=True)
            selected_clips = [clip for clip, _ in clips_with_duration[:job.num_clips_requested]]
            
            progress_callback.update_clip_selection(len(selected_clips))
            
            if not selected_clips:
                raise ValueError("No clips meet the minimum duration requirement (30+ seconds)")
            
            # Step 4: Process each clip
            processed_clips = []
            
            for i, clip in enumerate(selected_clips, 1):
                progress_callback.update_clip_processing(i, "Extracting clip...")
                
                start_time = clip.start_time
                end_time = clip.end_time
                duration = end_time - start_time
                
                # Get clip text for filename
                clip_words = [w.text for w in transcription.words 
                             if start_time <= w.start_time <= end_time]
                clip_text = " ".join(clip_words[:10])  # First 10 words
                
                # Create filename
                safe_name = generator.sanitize_filename(clip_text)
                base_filename = f"clip_{i:02d}_{safe_name}"
                
                # Extract and process clip
                temp_clip = output_dir / f"{base_filename}_temp.mp4"
                final_clip = output_dir / f"{base_filename}.mp4"
                caption_file = output_dir / f"{base_filename}.json"
                
                # Extract high-quality clip
                progress_callback.update_clip_processing(i, "Extracting high-quality clip...")
                if not generator.extract_high_quality_clip(str(input_file), str(temp_clip), 
                                                         start_time, end_time):
                    print(f"⚠️ Failed to extract clip {i}, skipping...")
                    continue
                
                # Auto-crop to target ratio
                progress_callback.update_clip_processing(i, "Auto-cropping with YOLO...")
                if not generator.auto_crop_with_yolo(str(temp_clip), str(final_clip), target_ratio):
                    print(f"⚠️ Failed to crop clip {i}, skipping...")
                    if temp_clip.exists():
                        temp_clip.unlink()
                    continue
                
                # Generate caption JSON
                progress_callback.update_clip_processing(i, "Generating captions...")
                full_clip_text = " ".join(clip_words)
                caption_data = generator.generate_caption_json(transcription, clip, full_clip_text)
                
                with open(caption_file, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(caption_data, f, indent=2, ensure_ascii=False)
                
                # Upload to S3 if using S3 storage
                if config.STORAGE_TYPE.split('#')[0].strip() == 's3':
                    progress_callback.update_clip_processing(i, "Uploading to S3...")
                    
                    # Upload clip file
                    clip_s3_path = f"results/{job.processing_id}/{final_clip.name}"
                    if not storage.save_file(str(final_clip), clip_s3_path):
                        logger.error(f"Failed to upload clip to S3: {clip_s3_path}")
                    
                    # Upload caption file
                    caption_s3_path = f"results/{job.processing_id}/{caption_file.name}"
                    if not storage.save_file(str(caption_file), caption_s3_path):
                        logger.error(f"Failed to upload caption to S3: {caption_s3_path}")
                
                # Clean up temp file
                if temp_clip.exists():
                    temp_clip.unlink()
                
                # Get file size
                file_size = final_clip.stat().st_size
                
                # Save clip info to database
                db_clip = GeneratedClip(
                    job_id=job_id,
                    clip_number=i,
                    clip_filename=final_clip.name,
                    caption_filename=caption_file.name,
                    duration_seconds=duration,
                    file_size_bytes=file_size,
                    clip_text_preview=clip_text,
                    start_time=start_time,
                    end_time=end_time
                )
                db.add(db_clip)
                
                processed_clips.append({
                    "clip_number": i,
                    "filename": final_clip.name,
                    "duration": duration,
                    "file_size": file_size
                })
                
                progress_callback.update_clip_completed(i)
                
                # Clean up memory after each clip
                cleanup_memory()
            
            # Cleanup temporary input file if downloaded from S3
            if temp_input_file and os.path.exists(temp_input_file.name):
                try:
                    os.unlink(temp_input_file.name)
                    logger.info(f"🧹 Cleaned up temporary file: {temp_input_file.name}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temporary file: {cleanup_error}")
            
            # Update final job status
            job.total_clips_generated = len(processed_clips)
            update_job_status(db, job_id, "completed")
            update_job_progress(db, job_id, 100, f"Completed! Generated {len(processed_clips)} clips")
            
            db.commit()
            print(f"✅ Successfully processed video for job {job.processing_id}")
            
            return {
                "status": "completed",
                "clips_generated": len(processed_clips),
                "clips": processed_clips
            }
            
        except Exception as e:
            # Cleanup temporary input file if it exists
            if temp_input_file and os.path.exists(temp_input_file.name):
                try:
                    os.unlink(temp_input_file.name)
                    logger.info(f"🧹 Cleaned up temporary file after error: {temp_input_file.name}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temporary file after error: {cleanup_error}")
            
            error_msg = f"Error processing video: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            try:
                update_job_status(db, job_id, "failed", error_msg)
            except SQLAlchemyError as db_error:
                logger.error(f"Failed to update error status: {db_error}")
            raise self.retry(exc=e, countdown=5 * (self.request.retries + 1))

@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Called when Celery worker is ready"""
    from database import init_database
    
    print("🗄️  Initializing worker database...")
    try:
        init_database()
        print("✅ Worker database initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize worker database: {e}")
        # Don't fail the worker startup, but log the error
        logger.error(f"Database initialization failed: {e}")
    
    print("🚀 Celery worker is ready and waiting for tasks...") 