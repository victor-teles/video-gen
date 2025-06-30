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