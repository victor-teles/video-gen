"""
Video processing orchestration service
Adapted from backend2 for use with backend architecture
This replaces the ClipGenerator class with a working implementation
"""
import os
import uuid
import logging
import time
from pathlib import Path

# Use backend's config and storage
import config
from storage_handler import StorageHandler

# Import the working services
from .highlights import HighlightsService
from .transcription import TranscriptionService
from .edit import EditService
from .subtitles import SubtitlesService

# Initialize logger
logger = logging.getLogger(__name__)

class VideoClipsService:
    """
    Service for processing videos into clips using the backend2 approach
    This replaces the broken ClipGenerator with working functionality
    """
    
    def __init__(self):
        """Initialize the video clips service"""
        # Initialize backend2 services
        self.transcription_service = TranscriptionService()
        self.highlights_service = HighlightsService()
        self.edit_service = EditService()
        self.subtitles_service = SubtitlesService()
        
        # Initialize storage handler (backend's existing system)
        self.storage = StorageHandler()
        
        # Check service availability
        self.transcription_available = (
            hasattr(self.transcription_service, 'whisperx_available') and 
            self.transcription_service.whisperx_available
        ) or (
            hasattr(self.transcription_service, 'faster_whisper_available') and 
            self.transcription_service.faster_whisper_available
        )
        
        logger.info(f"VideoClipsService initialized - Transcription available: {self.transcription_available}")
    
    async def process_video(self, video_path, num_clips=3, target_ratio=(9, 16), 
                          output_dir=None, progress_callback=None):
        """
        Process a video to create short vertical clips using backend2 approach
        
        Args:
            video_path: Path to the video file
            num_clips: Number of clips to generate
            target_ratio: Target aspect ratio tuple (width, height)
            output_dir: Output directory for clips
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of dictionaries containing clip information
        """
        try:
            # Generate a unique job ID
            job_id = str(uuid.uuid4())
            logger.info(f"Starting video processing job {job_id} for {video_path}")
            
            if progress_callback:
                progress_callback.update_transcription("Starting video processing...")
            
            # Step 1: Extract audio from video
            logger.info("Step 1: Extracting audio from video")
            start_time = time.time()
            audio_path = await self.edit_service.extract_audio(video_path)
            if not audio_path:
                raise Exception("Failed to extract audio from video")
            logger.info(f"Audio extraction completed in {time.time() - start_time:.2f} seconds")
            
            processed_clips = []
            word_level_data = None
            
            # Try transcription-based processing first if available
            transcriptions = None
            word_level_data = None
            
            if self.transcription_available:
                # Step 2: Try to transcribe audio
                if progress_callback:
                    progress_callback.update_transcription("Transcribing audio...")
                
                logger.info("Step 2: Attempting audio transcription")
                start_time = time.time()
                try:
                    transcriptions, word_level_data = await self.transcription_service.transcribe_audio(audio_path)
                    if transcriptions and len(transcriptions) > 0:
                        logger.info(f"Transcription completed in {time.time() - start_time:.2f} seconds")
                        logger.info(f"Word-level timestamps available: {word_level_data is not None}")
                    else:
                        logger.warning("Transcription returned no results, falling back to simple segmentation")
                        transcriptions = None
                except Exception as e:
                    logger.warning(f"Transcription failed: {e}, falling back to simple segmentation")
                    transcriptions = None
            
            # If we have transcriptions, use AI-powered highlight detection
            if transcriptions and len(transcriptions) > 0:
                
                # Format transcript for OpenRouter
                transcript_text = await self.subtitles_service.format_transcript(transcriptions)
                
                # Step 3: Get highlights using AI
                if progress_callback:
                    progress_callback.update_clip_finding(0)
                
                logger.info(f"Step 3: Finding {num_clips} highlights")
                start_time = time.time()
                highlights = await self.highlights_service.get_highlights(transcript_text, num_clips)
                if not highlights:
                    raise Exception("Failed to get highlights")
                logger.info(f"Highlight detection completed in {time.time() - start_time:.2f} seconds")
                
                if progress_callback:
                    progress_callback.update_clip_selection(len(highlights))
                
                # Step 4: Process each highlight
                logger.info(f"Step 4: Processing {len(highlights)} highlights")
                
                for i, highlight in enumerate(highlights, 1):
                    start_time_proc = time.time()
                    start_time_clip = highlight["start_time"]
                    end_time_clip = highlight["end_time"]
                    reason = highlight.get("reason", "Interesting segment")
                    title = highlight.get("title", f"Clip {i}")
                    
                    if progress_callback:
                        progress_callback.update_clip_processing(i, f"Processing {title}")
                    
                    logger.info(f"Processing highlight {i}/{len(highlights)}: {start_time_clip:.2f}s to {end_time_clip:.2f}s")
                    logger.info(f"Title: {title}")
                    logger.info(f"Reason: {reason}")
                    
                    clip_info = await self._process_clip(
                        video_path=video_path,
                        start_time=start_time_clip,
                        end_time=end_time_clip,
                        clip_number=i,
                        transcriptions=transcriptions,
                        reason=reason,
                        title=title,
                        word_level_data=word_level_data,
                        target_ratio=target_ratio,
                        output_dir=output_dir
                    )
                    
                    if clip_info:
                        processed_clips.append(clip_info)
                        
                        if progress_callback:
                            progress_callback.update_clip_completed(i)
                    
                    logger.info(f"Highlight {i} processed in {time.time() - start_time_proc:.2f} seconds")
            else:
                # Transcription not available, split video into equal parts
                logger.warning("Transcription service not available - splitting video into equal parts")
                
                # Get video duration
                video_duration = await self.edit_service.get_video_duration(video_path)
                if not video_duration:
                    raise Exception("Failed to get video duration")
                
                # Create clips by dividing the video into equal parts
                segment_duration = video_duration / num_clips
                for i in range(num_clips):
                    start_time_proc = time.time()
                    start_time_clip = i * segment_duration
                    end_time_clip = min((i + 1) * segment_duration, video_duration)
                    
                    if progress_callback:
                        progress_callback.update_clip_processing(i+1, f"Processing segment {i+1}")
                    
                    logger.info(f"Processing segment {i+1}/{num_clips}: {start_time_clip:.2f}s to {end_time_clip:.2f}s")
                    
                    clip_info = await self._process_clip(
                        video_path=video_path,
                        start_time=start_time_clip,
                        end_time=end_time_clip,
                        clip_number=i+1,
                        transcriptions=None,
                        reason="Auto-segmented clip",
                        title=f"Segment {i+1}",
                        word_level_data=None,
                        target_ratio=target_ratio,
                        output_dir=output_dir
                    )
                    
                    if clip_info:
                        processed_clips.append(clip_info)
                        
                        if progress_callback:
                            progress_callback.update_clip_completed(i+1)
                    
                    logger.info(f"Segment {i+1} processed in {time.time() - start_time_proc:.2f} seconds")
            
            # Cleanup temporary audio file
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup audio file {audio_path}: {e}")
            
            logger.info(f"Video processing completed. Generated {len(processed_clips)} clips.")
            return processed_clips
            
        except Exception as e:
            logger.error(f"Error processing video: {str(e)}", exc_info=True)
            # Return partial results if we have any processed clips
            if processed_clips:
                logger.info(f"Returning {len(processed_clips)} successfully processed clips despite error")
                return processed_clips
            raise
    
    async def _process_clip(self, video_path, start_time, end_time, clip_number, 
                          transcriptions=None, reason="", title=None, 
                          word_level_data=None, target_ratio=(9, 16), output_dir=None):
        """Process a single clip from the video"""
        try:
            # Use provided title or generate one
            if not title:
                # Create safe filename from reason
                safe_reason = "".join(c for c in reason if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_reason = safe_reason.replace(' ', '_')[:30]  # Limit length
                title = f"clip_{clip_number:02d}_{safe_reason}" if safe_reason else f"clip_{clip_number:02d}"
            else:
                # Make title filename-safe
                title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
                title = title.replace(' ', '_')
                title = f"clip_{clip_number:02d}_{title}"
            
            # Ensure output directory
            if not output_dir:
                output_dir = config.RESULTS_DIR / "default_processing"
            
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate output paths
            clip_filename = f"{title}.mp4"
            clip_path = output_dir / clip_filename
            
            # Generate clips using edit service
            success = await self.edit_service.crop_video(
                input_file=str(video_path),
                output_file=str(clip_path),
                start_time=start_time,
                end_time=end_time
            )
            
            if not success:
                logger.error(f"Failed to generate clip {clip_number}")
                return None
            
            # Create subtitle files if transcriptions are available
            subtitle_filename = None
            word_timestamps_filename = None
            
            if transcriptions:
                # Create SRT subtitle file
                subtitle_filename = f"{title}.srt"
                subtitle_path = output_dir / subtitle_filename
                
                await self.subtitles_service.create_subtitle(
                    transcriptions, start_time, end_time, str(subtitle_path)
                )
                
                # Create word-level timestamps JSON if available
                if word_level_data:
                    word_timestamps_filename = f"{title}_words.json"
                    word_timestamps_path = output_dir / word_timestamps_filename
                    
                    await self.subtitles_service.create_word_level_timestamps(
                        word_level_data, start_time, end_time, str(word_timestamps_path)
                    )
            
            # Get clip file size
            clip_size = clip_path.stat().st_size if clip_path.exists() else 0
            duration = end_time - start_time
            
            # Return clip information in the expected format for backend
            clip_info = {
                "clip_number": clip_number,
                "clip_filename": clip_filename,
                "caption_filename": subtitle_filename,
                "word_timestamps_filename": word_timestamps_filename,
                "duration_seconds": duration,
                "file_size_bytes": clip_size,
                "clip_text_preview": reason[:100] if reason else f"Clip {clip_number}",
                "start_time": start_time,
                "end_time": end_time,
                "title": title,
                "reason": reason
            }
            
            logger.info(f"Successfully processed clip {clip_number}: {clip_filename}")
            return clip_info
            
        except Exception as e:
            logger.error(f"Error processing clip {clip_number}: {str(e)}", exc_info=True)
            return None