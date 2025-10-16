#!/usr/bin/env python3
"""
Cleanup script to mark stuck/abandoned processing jobs as failed.
Run this periodically or as a cron job to clean up jobs that were killed by OOM.
"""
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from database import SessionLocal
from models import ProcessingJob
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def cleanup_stuck_jobs(max_processing_time_minutes=30):
    """
    Mark jobs stuck in 'processing' status for too long as failed.
    
    Args:
        max_processing_time_minutes: Max time a job should be processing before marked as stuck
    """
    db = SessionLocal()
    try:
        # Find jobs that have been processing for too long
        cutoff_time = datetime.utcnow() - timedelta(minutes=max_processing_time_minutes)
        
        stuck_jobs = db.query(ProcessingJob).filter(
            ProcessingJob.status == "processing",
            ProcessingJob.started_at < cutoff_time
        ).all()
        
        if not stuck_jobs:
            logger.info("No stuck jobs found")
            return 0
        
        logger.info(f"Found {len(stuck_jobs)} stuck jobs")
        
        for job in stuck_jobs:
            processing_time = datetime.utcnow() - job.started_at if job.started_at else None
            logger.info(f"Marking job {job.processing_id} as failed (stuck for {processing_time})")
            
            job.status = "failed"
            job.error_message = (
                "Processing timed out - likely due to insufficient memory. "
                "The video may be too large or complex. Please try with a shorter video "
                "or contact support for assistance with large files."
            )
            job.completed_at = datetime.utcnow()
            
            if job.started_at:
                job.processing_time_seconds = int((datetime.utcnow() - job.started_at).total_seconds())
        
        db.commit()
        logger.info(f"Successfully marked {len(stuck_jobs)} jobs as failed")
        return len(stuck_jobs)
        
    except Exception as e:
        logger.error(f"Error cleaning up stuck jobs: {e}")
        db.rollback()
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Cleanup stuck video processing jobs")
    parser.add_argument(
        "--max-time",
        type=int,
        default=30,
        help="Maximum processing time in minutes before job is marked as stuck (default: 30)"
    )
    
    args = parser.parse_args()
    
    logger.info(f"Starting cleanup with max processing time: {args.max_time} minutes")
    cleaned = cleanup_stuck_jobs(args.max_time)
    logger.info(f"Cleanup complete. Processed {cleaned} jobs")
    
    sys.exit(0)
