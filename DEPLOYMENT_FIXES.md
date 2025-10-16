# Video Processing OOM Fix - Deployment Guide

## Problem Summary
Video processing jobs are getting stuck in "processing" status because the Celery worker is being **killed by Linux OOM (Out of Memory) killer** during WhisperX transcription. The worker restarts but the job remains in processing state with no error message.

## Root Cause
- WhisperX AI model loads into memory during transcription
- On longer videos or with limited RAM, the process exceeds available memory
- Linux kernel kills the worker process with SIGKILL
- Job is never marked as failed, remains stuck at "processing"

## Fixes Implemented

### 1. Memory Optimization in Transcription Service
**File**: `backend/services/transcription.py`
- Added garbage collection before/after transcription steps
- Reduced batch size from default to 8 for memory efficiency
- Disabled character-level alignments to save memory
- Added torch CUDA cache clearing on GPU systems
- Added cleanup on errors

### 2. Celery Worker Configuration
**File**: `backend/tasks.py`
- Added memory limits: `worker_max_memory_per_child=2000000` (2GB)
- Added time limits: 30min soft, 35min hard
- Reduced max retries from 3 to 1 (avoid repeated OOM kills)
- Added detection of stuck jobs (processing > 20min = likely killed)
- Improved error messages for memory issues
- Added memory cleanup after each job

### 3. Stuck Job Cleanup Script
**File**: `backend/cleanup_stuck_jobs.py`
- Marks jobs stuck in processing > 20-30min as failed
- Provides clear error message about memory limits
- Can be run manually or as cron job

## Deployment Steps

### Step 1: Deploy Code Changes to EC2

```bash
# SSH into EC2
ssh ubuntu@api.editur.ai

# Navigate to backend
cd /opt/editur-ai/backend

# Pull latest changes
git pull origin main

# OR if you haven't committed, copy files manually:
# Use scp or rsync to upload:
# - backend/services/transcription.py
# - backend/tasks.py
# - backend/cleanup_stuck_jobs.py
```

### Step 2: Run Cleanup Script

```bash
# Activate virtual environment
source /opt/editur-ai/backend/venv/bin/activate

# Run cleanup to mark current stuck jobs as failed
python cleanup_stuck_jobs.py --max-time 20

# Check logs
sudo journalctl -u editur-worker -n 50
```

### Step 3: Restart Services

```bash
# Restart worker with new configuration
sudo systemctl restart editur-worker

# Verify worker is running
sudo systemctl status editur-worker

# Restart API (if needed)
sudo systemctl restart editur-api
sudo systemctl status editur-api
```

### Step 4: Set Up Automated Cleanup (Optional but Recommended)

```bash
# Create cron job to cleanup stuck jobs every 30 minutes
sudo crontab -e

# Add this line:
*/30 * * * * /opt/editur-ai/backend/venv/bin/python /opt/editur-ai/backend/cleanup_stuck_jobs.py --max-time 30 >> /var/log/editur-cleanup.log 2>&1
```

## Verification

### Test with the Stuck Job
1. The cleanup script should have marked job `91bb5c6c-484c-4c8f-a271-6622662c4f06` as failed
2. Check via API:
   ```bash
   curl https://api.editur.ai/api/v1/videos/91bb5c6c-484c-4c8f-a271-6622662c4f06/status
   ```
3. Should show status: "failed" with error message about memory

### Test New Video Upload
1. Upload a test video via /docs interface
2. Monitor worker logs: `sudo journalctl -u editur-worker -f`
3. Should see improved memory management and cleanup messages

## Long-Term Solutions

### Option 1: Upgrade EC2 Instance (Recommended)
Current instance may have limited RAM. Consider:
- Upgrade to instance type with more RAM (t3.large → t3.xlarge or similar)
- Add swap space temporarily:
  ```bash
  sudo fallocate -l 4G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  ```

### Option 2: Use Smaller Whisper Model
Edit `backend/config.py` or `.env`:
```bash
WHISPER_MODEL_SIZE=tiny  # Instead of 'base' or 'small'
```

### Option 3: Process in Chunks
For very long videos (>10min), implement chunking:
- Split audio into smaller segments
- Process each segment separately
- Combine results

### Option 4: Use Faster Whisper Instead
Faster Whisper uses less memory than WhisperX.
The code already has fallback logic to use it if WhisperX fails.

## Monitoring

### Check Worker Memory Usage
```bash
# Real-time memory monitoring
watch -n 1 'ps aux | grep celery | grep -v grep'

# Or use htop
htop -p $(pgrep -f celery)
```

### Check for OOM Kills
```bash
# Check system logs for OOM kills
sudo dmesg | grep -i "killed process"

# Or check journalctl
sudo journalctl -k | grep -i "out of memory"
```

### Monitor Job Status
```bash
# Watch worker logs in real-time
sudo journalctl -u editur-worker -f

# Check recent errors
sudo journalctl -u editur-worker --since "1 hour ago" | grep ERROR
```

## Rollback Plan

If issues occur after deployment:

```bash
# Stop services
sudo systemctl stop editur-worker
sudo systemctl stop editur-api

# Restore previous version
cd /opt/editur-ai/backend
git checkout <previous-commit-hash>

# Restart services
sudo systemctl start editur-worker
sudo systemctl start editur-api
```

## Support

If videos continue to get stuck:
1. Check EC2 instance RAM: `free -h`
2. Check worker concurrency in systemd config
3. Consider implementing video file size/duration limits
4. Contact for assistance with specific large files
