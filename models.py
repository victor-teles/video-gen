"""
Database models for the Video Clip Generator API
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

class ProcessingJob(Base):
    """Model for tracking video processing jobs"""
    __tablename__ = "processing_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    processing_id = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # Job status
    status = Column(String, default="pending")  # pending, processing, completed, failed
    progress_percentage = Column(Integer, default=0)
    current_step = Column(String, default="Queued")
    
    # Input parameters
    input_filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    num_clips_requested = Column(Integer, nullable=False)
    aspect_ratio = Column(String, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Results and errors
    error_message = Column(Text, nullable=True)
    total_clips_generated = Column(Integer, default=0)
    processing_time_seconds = Column(Integer, nullable=True)
    
    # Relationships
    clips = relationship("GeneratedClip", back_populates="job", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            "processing_id": self.processing_id,
            "status": self.status,
            "progress": self.progress_percentage,
            "current_step": self.current_step,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "total_clips": self.total_clips_generated,
            "processing_time": self.processing_time_seconds,
            "input_filename": self.original_filename,
            "num_clips_requested": self.num_clips_requested,
            "aspect_ratio": self.aspect_ratio
        }

class GeneratedClip(Base):
    """Model for storing information about generated clips"""
    __tablename__ = "generated_clips"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("processing_jobs.id"))
    
    # Clip information
    clip_number = Column(Integer, nullable=False)
    clip_filename = Column(String, nullable=False)
    caption_filename = Column(String, nullable=False)
    
    # Clip metadata
    duration_seconds = Column(Float, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    clip_text_preview = Column(Text, nullable=False)  # First few words for preview
    
    # Timestamps from original video
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    
    # Relationships
    job = relationship("ProcessingJob", back_populates="clips")
    
    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            "clip_id": self.clip_number,
            "filename": self.clip_filename,
            "duration": self.duration_seconds,
            "preview_text": self.clip_text_preview,
            "file_size": f"{self.file_size_bytes / (1024*1024):.1f}MB",
            "start_time": self.start_time,
            "end_time": self.end_time,
            "download_url": f"/api/download/clips/{self.job.processing_id}/{self.clip_filename}",
            "captions_url": f"/api/download/captions/{self.job.processing_id}/{self.caption_filename}"
        }

class FacelessVideoJob(Base):
    """Model for tracking faceless video generation jobs"""
    __tablename__ = "faceless_video_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    processing_id = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # Job status
    status = Column(String, default="pending")  # pending, processing, completed, failed
    progress_percentage = Column(Integer, default=0)
    current_step = Column(String, default="Queued")
    
    # Input parameters (following user requirements)
    story_title = Column(String, nullable=False)
    story_description = Column(Text, nullable=True)
    story_content = Column(Text, nullable=True)  # User-provided content
    story_category = Column(String, nullable=False)  # Story category/type
    image_style = Column(String, nullable=False)  # Image generation style
    voice_id = Column(String, nullable=False)  # TTS voice selection
    aspect_ratio = Column(String, default="9:16")
    
    # Generation settings
    max_scenes = Column(Integer, default=14)
    char_limit_min = Column(Integer, default=700)
    char_limit_max = Column(Integer, default=800)
    speech_rate = Column(Float, default=1.1)
    
    # Results
    generated_story = Column(Text, nullable=True)  # Final processed story
    final_video_filename = Column(String, nullable=True)
    caption_filename = Column(String, nullable=True)  # JSON caption file
    total_scenes_generated = Column(Integer, default=0)
    total_duration_seconds = Column(Float, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    
    # Cost tracking (for API usage)
    openai_cost = Column(Float, default=0.0)
    replicate_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    processing_time_seconds = Column(Integer, nullable=True)
    
    # Relationships
    scenes = relationship("FacelessVideoScene", back_populates="job", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            "processing_id": self.processing_id,
            "status": self.status,
            "progress": self.progress_percentage,
            "current_step": self.current_step,
            "story_title": self.story_title,
            "story_description": self.story_description,
            "story_category": self.story_category,
            "image_style": self.image_style,
            "voice_id": self.voice_id,
            "aspect_ratio": self.aspect_ratio,
            "total_scenes": self.total_scenes_generated,
            "duration": self.total_duration_seconds,
            "file_size": f"{self.file_size_bytes / (1024*1024):.1f}MB" if self.file_size_bytes else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "processing_time": self.processing_time_seconds,
            "estimated_cost": f"${self.total_cost:.4f}" if self.total_cost else None,
            "download_url": f"/api/download/faceless-video/{self.processing_id}" if self.final_video_filename else None,
            "captions_url": f"/api/download/faceless-captions/{self.processing_id}" if self.caption_filename else None,
            "error_message": self.error_message
        }

class FacelessVideoScene(Base):
    """Model for storing individual scenes in faceless videos"""
    __tablename__ = "faceless_video_scenes"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("faceless_video_jobs.id"))
    
    # Scene information
    scene_number = Column(Integer, nullable=False)
    scene_text = Column(Text, nullable=False)  # Narrator text for this scene
    image_prompt = Column(Text, nullable=False)  # AI image generation prompt
    
    # Generated content
    image_filename = Column(String, nullable=True)  # Generated image file
    audio_filename = Column(String, nullable=True)  # Generated TTS audio file
    image_url = Column(String, nullable=True)  # Original image URL from API
    
    # Timing information (for word-level captions)
    start_time = Column(Float, nullable=False)  # Start time in final video
    end_time = Column(Float, nullable=False)    # End time in final video
    duration = Column(Float, nullable=False)    # Scene duration
    
    # Generation metadata
    image_generation_time = Column(Float, nullable=True)
    audio_generation_time = Column(Float, nullable=True)
    
    # Relationships
    job = relationship("FacelessVideoJob", back_populates="scenes")
    
    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            "scene_number": self.scene_number,
            "text": self.scene_text,
            "image_prompt": self.image_prompt,
            "duration": self.duration,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "image_url": self.image_url,
            "has_audio": bool(self.audio_filename),
            "has_image": bool(self.image_filename)
        } 