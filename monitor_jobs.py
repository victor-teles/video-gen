#!/usr/bin/env python3
"""
Monitor video processing jobs and worker health.
Useful for debugging and identifying stuck jobs in real-time.
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def monitor_jobs():
    """Display current status of all processing jobs"""
    db = SessionLocal()
    try:
        # Get counts by status
        total = db.query(ProcessingJob).count()
        pending = db.query(ProcessingJob).filter(ProcessingJob.status == "pending").count()
        processing = db.query(ProcessingJob).filter(ProcessingJob.status == "processing").count()
        completed = db.query(ProcessingJob).filter(ProcessingJob.status == "completed").count()
        failed = db.query(ProcessingJob).filter(ProcessingJob.status == "failed").count()
        
        print("\n" + "="*80)
        print("VIDEO PROCESSING JOBS STATUS")
        print("="*80)
        print(f"Total Jobs:      {total}")
        print(f"Pending:         {pending}")
        print(f"Processing:      {processing}")
        print(f"Completed:       {completed}")
        print(f"Failed:          {failed}")
        print("="*80)
        
        # Show currently processing jobs
        if processing > 0:
            print("\nCURRENTLY PROCESSING JOBS:")
            print("-"*80)
            processing_jobs = db.query(ProcessingJob).filter(
                ProcessingJob.status == "processing"
            ).order_by(ProcessingJob.started_at.desc()).all()
            
            for job in processing_jobs:
                duration = None
                if job.started_at:
                    duration = datetime.utcnow() - job.started_at
                    duration_str = str(duration).split('.')[0]  # Remove microseconds
                else:
                    duration_str = "Not started"
                
                # Check if potentially stuck
                is_stuck = duration and duration > timedelta(minutes=20)
                stuck_marker = " ⚠️  STUCK?" if is_stuck else ""
                
                print(f"\nJob ID: {job.processing_id}{stuck_marker}")
                print(f"  File: {job.original_filename}")
                print(f"  Progress: {job.progress_percentage}% - {job.current_step}")
                print(f"  Duration: {duration_str}")
                print(f"  Started: {job.started_at}")
                print(f"  Clips Requested: {job.num_clips_requested}")
        
        # Show recent failures
        recent_failures = db.query(ProcessingJob).filter(
            ProcessingJob.status == "failed",
            ProcessingJob.completed_at >= datetime.utcnow() - timedelta(hours=24)
        ).order_by(ProcessingJob.completed_at.desc()).limit(5).all()
        
        if recent_failures:
            print("\n" + "="*80)
            print("RECENT FAILURES (Last 24 hours):")
            print("-"*80)
            for job in recent_failures:
                print(f"\nJob ID: {job.processing_id}")
                print(f"  File: {job.original_filename}")
                print(f"  Failed: {job.completed_at}")
                error = job.error_message[:200] + "..." if job.error_message and len(job.error_message) > 200 else job.error_message
                print(f"  Error: {error}")
        
        # Show recent completions
        recent_completed = db.query(ProcessingJob).filter(
            ProcessingJob.status == "completed",
            ProcessingJob.completed_at >= datetime.utcnow() - timedelta(hours=24)
        ).order_by(ProcessingJob.completed_at.desc()).limit(5).all()
        
        if recent_completed:
            print("\n" + "="*80)
            print("RECENT COMPLETIONS (Last 24 hours):")
            print("-"*80)
            for job in recent_completed:
                duration = "N/A"
                if job.processing_time_seconds:
                    minutes = job.processing_time_seconds // 60
                    seconds = job.processing_time_seconds % 60
                    duration = f"{minutes}m {seconds}s"
                
                print(f"\nJob ID: {job.processing_id}")
                print(f"  File: {job.original_filename}")
                print(f"  Completed: {job.completed_at}")
                print(f"  Processing Time: {duration}")
                print(f"  Clips Generated: {job.total_clips_generated}")
        
        print("\n" + "="*80 + "\n")
        
    except Exception as e:
        logger.error(f"Error monitoring jobs: {e}")
    finally:
        db.close()


def check_stuck_jobs():
    """Check for potentially stuck jobs and list them"""
    db = SessionLocal()
    try:
        cutoff_time = datetime.utcnow() - timedelta(minutes=20)
        
        stuck_jobs = db.query(ProcessingJob).filter(
            ProcessingJob.status == "processing",
            ProcessingJob.started_at < cutoff_time
        ).all()
        
        if stuck_jobs:
            print("\n" + "!"*80)
            print(f"WARNING: Found {len(stuck_jobs)} potentially stuck jobs!")
            print("!"*80)
            for job in stuck_jobs:
                duration = datetime.utcnow() - job.started_at if job.started_at else None
                print(f"\nJob ID: {job.processing_id}")
                print(f"  File: {job.original_filename}")
                print(f"  Stuck for: {duration}")
                print(f"  Last step: {job.current_step}")
                print(f"  Progress: {job.progress_percentage}%")
            
            print("\nRun cleanup_stuck_jobs.py to mark these as failed")
            print("!"*80 + "\n")
            return len(stuck_jobs)
        else:
            print("\n✅ No stuck jobs detected\n")
            return 0
            
    except Exception as e:
        logger.error(f"Error checking stuck jobs: {e}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor video processing jobs")
    parser.add_argument(
        "--check-stuck",
        action="store_true",
        help="Only check for stuck jobs"
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuously monitor (refresh every 5 seconds)"
    )
    
    args = parser.parse_args()
    
    if args.watch:
        import time
        try:
            while True:
                os.system('clear' if os.name == 'posix' else 'cls')
                monitor_jobs()
                if args.check_stuck:
                    check_stuck_jobs()
                print("Refreshing in 5 seconds... (Ctrl+C to stop)")
                time.sleep(5)
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")
    elif args.check_stuck:
        stuck_count = check_stuck_jobs()
        sys.exit(0 if stuck_count == 0 else 1)
    else:
        monitor_jobs()
        check_stuck_jobs()
