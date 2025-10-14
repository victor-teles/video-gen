"""
Video processing service integrated from backend2
This contains the working video processing pipeline
"""
import os
import uuid
import logging
import time
from pathlib import Path

# Import backend2's services that we copied
from .highlights import HighlightsService
from .transcription import TranscriptionService
from .edit import EditService
from .subtitles import SubtitlesService

# Initialize logger
logger = logging.getLogger(__name__)

class VideoService:
    """Video processing service with backend2's proven implementation"""
    
    def __init__(self):
        """Initialize the video service"""
        self.edit_service = EditService()
        self.transcription_service = TranscriptionService()
        self.highlights_service = HighlightsService()
        self.subtitles_service = SubtitlesService()
        
        # Check service availability
        self.transcription_available = (
            hasattr(self.transcription_service, 'whisperx_available') and 
            self.transcription_service.whisperx_available
        ) or (
            hasattr(self.transcription_service, 'faster_whisper_available') and 
            self.transcription_service.faster_whisper_available
        )
        
        logger.info(f"VideoService initialized - Transcription available: {self.transcription_available}")
    
    async def process_video(self, video_path, num_clips=3, burn_captions=False):
        """
        Process a video to create short vertical clips
        
        Args:
            video_path: Path to the video file
            num_clips: Number of clips to generate
            burn_captions: Whether to burn captions into the video
            
        Returns:
            Dictionary containing the processed clips information
        """
        try:
            # Generate a unique ID for this processing job
            job_id = str(uuid.uuid4())
            logger.info(f"Starting video processing job {job_id} for {video_path}")
            
            # Step 1: Extract audio from video
            logger.info("Step 1: Extracting audio from video")
            start_time = time.time()
            audio_path = await self.edit_service.extract_audio(video_path)
            if not audio_path:
                raise Exception("Failed to extract audio from video")
            logger.info(f"Audio extraction completed in {time.time() - start_time:.2f} seconds")
            
            processed_clips = []
            
            # Try transcription-based processing first if available
            transcriptions = None
            word_level_data = None
            
            if self.transcription_available:
                # Step 2: Try to transcribe audio
                logger.info("Step 2: Attempting audio transcription")
                start_time = time.time()
                try:
                    transcriptions, word_level_data = await self.transcription_service.transcribe_audio(audio_path)
                    if transcriptions and len(transcriptions) > 0:
                        logger.info(f"Transcription completed in {time.time() - start_time:.2f} seconds")
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
                
                # Step 3: Get highlights
                logger.info(f"Step 3: Finding {num_clips} highlights using AI")
                start_time = time.time()
                highlights = await self.highlights_service.get_highlights(transcript_text, num_clips)
                if highlights:
                    logger.info(f"Highlight detection completed in {time.time() - start_time:.2f} seconds")
                    
                    # Step 4: Process each highlight
                    logger.info(f"Step 4: Processing {len(highlights)} highlights")
                    
                    for i, highlight in enumerate(highlights, 1):
                        start_time_proc = time.time()
                        start_time_clip = highlight["start_time"]
                        end_time_clip = highlight["end_time"]
                        reason = highlight.get("reason", "Interesting segment")
                        title = highlight.get("title", f"Clip {i}")
                        
                        logger.info(f"Processing highlight {i}/{len(highlights)}: {start_time_clip:.2f}s to {end_time_clip:.2f}s")
                        
                        clip_info = await self._process_clip(
                            video_path=video_path,
                            start_time=start_time_clip,
                            end_time=end_time_clip,
                            clip_number=i,
                            transcriptions=transcriptions,
                            reason=reason,
                            title=title,
                            word_level_data=word_level_data
                        )
                        
                        if clip_info:
                            processed_clips.append(clip_info)
                        
                        logger.info(f"Highlight {i} processed in {time.time() - start_time_proc:.2f} seconds")
                else:
                    logger.warning("No highlights found, falling back to simple segmentation")
                    transcriptions = None  # Fallback to segmentation
            
            # If no transcriptions available, split video into equal parts
            if not transcriptions:
                logger.warning("Using simple video segmentation")
                
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
                    
                    logger.info(f"Processing segment {i+1}/{num_clips}: {start_time_clip:.2f}s to {end_time_clip:.2f}s")
                    
                    clip_info = await self._process_clip(
                        video_path=video_path,
                        start_time=start_time_clip,
                        end_time=end_time_clip,
                        clip_number=i+1,
                        transcriptions=None,
                        reason="Auto-segmented clip",
                        title=f"Segment {i+1}",
                        word_level_data=None
                    )
                    
                    if clip_info:
                        processed_clips.append(clip_info)
                    
                    logger.info(f"Segment {i+1} processed in {time.time() - start_time_proc:.2f} seconds")
            
            # Cleanup temporary audio file
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup audio file {audio_path}: {e}")
            
            logger.info(f"Video processing completed. Generated {len(processed_clips)} clips.")
            
            return {
                "job_id": job_id,
                "original_video": video_path,
                "processed_clips": processed_clips
            }
            
        except Exception as e:
            logger.error(f"Error processing video: {str(e)}", exc_info=True)
            # Return partial results if we have any processed clips
            if processed_clips:
                logger.info(f"Returning {len(processed_clips)} successfully processed clips despite error")
                return {
                    "job_id": job_id,
                    "original_video": video_path,
                    "processed_clips": processed_clips,
                    "error": str(e)
                }
            raise
    
    async def _process_clip(self, video_path, start_time, end_time, clip_number, 
                          transcriptions=None, reason="", title=None, word_level_data=None):
        """Process a single clip from the video"""
        try:
            # Use provided title or generate one
            if not title:
                safe_reason = "".join(c for c in reason if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_reason = safe_reason.replace(' ', '_')[:30]
                title = f"clip_{clip_number:02d}_{safe_reason}" if safe_reason else f"clip_{clip_number:02d}"
            else:
                title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
                title = title.replace(' ', '_')
                title = f"clip_{clip_number:02d}_{title}"
            
            # Import config here to avoid circular imports
            import config
            
            # Setup output directory
            output_dir = config.RESULTS_DIR / "clips_processing"
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
            if transcriptions:
                subtitle_filename = f"{title}.srt"
                subtitle_path = output_dir / subtitle_filename
                
                await self.subtitles_service.create_subtitle(
                    transcriptions, start_time, end_time, str(subtitle_path)
                )
            
            # Get clip file size and calculate duration
            clip_size = clip_path.stat().st_size if clip_path.exists() else 0
            duration = end_time - start_time
            
            # Get text from transcriptions if available
            full_text = ""
            if transcriptions:
                clip_words = []
                for text, t_start, t_end in transcriptions:
                    if start_time <= t_start <= end_time or start_time <= t_end <= end_time:
                        clip_words.append(text)
                full_text = " ".join(clip_words)
            
            # Return clip information
            return {
                "clip_number": clip_number,
                "clip_filename": clip_filename,
                "clip_path": str(clip_path),
                "caption_path": str(subtitle_path) if subtitle_filename else None,
                "duration": duration,
                "start_time": start_time,
                "end_time": end_time,
                "full_text": full_text,
                "file_size": clip_size
            }
            
        except Exception as e:
            logger.error(f"Error processing clip {clip_number}: {str(e)}", exc_info=True)
            return None