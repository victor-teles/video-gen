"""
Video editing service for processing videos
Adapted from backend2 for use with backend architecture
"""
import logging
import os
import subprocess
import uuid
from typing import Tuple
import sys
import shutil
from pathlib import Path

# Use backend's config module
import config

# Initialize logger
logger = logging.getLogger(__name__)

# Use backend's storage configuration for temp directory
TMP_DIR = config.PROCESSING_DIR
TMP_DIR.mkdir(parents=True, exist_ok=True)

logger.info(f"EditService temp directory: {TMP_DIR}")

class EditService:
    """Service for editing videos"""
    
    async def extract_audio(self, video_path):
        """
        Extract audio from a video file
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Path to the extracted audio file, or None if extraction failed
        """
        # Get the filename without extension
        video_filename = os.path.basename(video_path)
        filename_no_ext = os.path.splitext(video_filename)[0]
        
        # Generate output path
        audio_filename = f"{filename_no_ext}_{uuid.uuid4().hex}.mp3"
        audio_path = TMP_DIR / audio_filename
        
        logger.info(f"Extracting audio from {video_path} to {audio_path}")
        
        try:
            # Use ffmpeg directly for reliable audio extraction
            cmd = [
                "ffmpeg", "-i", str(video_path),
                "-q:a", "0", "-map", "a",
                "-y", str(audio_path)
            ]
            
            logger.info(f"Running ffmpeg command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and audio_path.exists() and audio_path.stat().st_size > 0:
                logger.info(f"Successfully extracted audio: {audio_path}")
                return str(audio_path)
            else:
                logger.error(f"Audio extraction failed with return code: {result.returncode}")
                logger.error(f"stderr: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting audio: {str(e)}", exc_info=True)
            return None

    async def crop_video(self, input_file, output_file, start_time, end_time):
        """
        Crop video to a specific time range and convert to 9:16 aspect ratio
        
        Args:
            input_file: Path to the input video file
            output_file: Path to the output video file
            start_time: Start time in seconds
            end_time: End time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Get video duration to ensure safe cropping
            video_duration = await self.get_video_duration(input_file)
            if not video_duration:
                logger.error(f"Could not determine video duration for {input_file}")
                return False
                
            # Ensure end_time doesn't exceed video duration
            safe_end_time = min(end_time, video_duration - 0.1)  # 0.1s buffer
            safe_start_time = min(start_time, safe_end_time - 1.0)  # Ensure at least 1 second
            
            logger.info(f"Cropping video from {safe_start_time}s to {safe_end_time}s")
            
            # Calculate duration
            duration = safe_end_time - safe_start_time
            
            # Use ffmpeg for cropping and aspect ratio conversion to 9:16
            cmd = [
                "ffmpeg", "-i", input_file,
                "-ss", str(safe_start_time),
                "-t", str(duration),
                "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", str(config.VIDEO_CRF),
                "-c:a", "aac",
                "-b:a", config.AUDIO_BITRATE,
                "-y", output_file
            ]
                
            logger.info(f"Running ffmpeg command: {' '.join(cmd)}")
            
            # Execute command
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"ffmpeg command failed with return code {result.returncode}")
                logger.error(f"stderr: {result.stderr}")
                return False
                
            # Verify output exists
            if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                logger.error(f"Output file was not created or is empty: {output_file}")
                return False
                
            logger.info(f"Successfully cropped video: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error cropping video: {str(e)}", exc_info=True)
            return False

    async def get_video_duration(self, video_path):
        """
        Get the duration of a video file in seconds
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Duration in seconds, or None if failed
        """
        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                "-of", "csv=p=0", video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                logger.info(f"Video duration: {duration} seconds")
                return duration
            else:
                logger.error(f"ffprobe failed with return code: {result.returncode}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting video duration: {str(e)}", exc_info=True)
            return None

    async def resize_to_aspect_ratio(self, input_file, output_file, target_ratio=(9, 16)):
        """
        Resize video to target aspect ratio (used for final output)
        
        Args:
            input_file: Path to input video
            output_file: Path to output video
            target_ratio: Tuple of (width_ratio, height_ratio)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Calculate target resolution for 9:16 (1080x1920 is standard)
            if target_ratio == (9, 16):
                width, height = 1080, 1920
            elif target_ratio == (1, 1):
                width, height = 1080, 1080
            elif target_ratio == (16, 9):
                width, height = 1920, 1080
            else:
                # Custom ratio - use 1080p as base
                ratio = target_ratio[0] / target_ratio[1]
                if ratio > 1:  # Landscape
                    width, height = 1920, int(1920 / ratio)
                else:  # Portrait
                    width, height = int(1080 * ratio), 1080
            
            cmd = [
                "ffmpeg", "-i", input_file,
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
                "-c:v", "libx264",
                "-preset", "fast", 
                "-crf", str(config.VIDEO_CRF),
                "-c:a", "aac",
                "-b:a", config.AUDIO_BITRATE,
                "-y", output_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Successfully resized video to {width}x{height}")
                return True
            else:
                logger.error(f"Video resize failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error resizing video: {str(e)}", exc_info=True)
            return False