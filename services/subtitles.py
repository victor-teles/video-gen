"""
Subtitles generation service
Adapted from backend2 for use with backend architecture
"""
import os
import logging
import textwrap
import json

# Initialize logger
logger = logging.getLogger(__name__)

class SubtitlesService:
    """Service for generating subtitles from transcriptions"""
    
    async def create_subtitle(self, transcriptions, highlight_start, highlight_end, output_file):
        """
        Create subtitles for the highlight clip.
        
        Args:
            transcriptions: List of (text, start_time, end_time) tuples
            highlight_start: Start time of the highlight clip
            highlight_end: End time of the highlight clip
            output_file: Path to the output SRT file
        
        Returns:
            bool: True if subtitles were successfully created, False otherwise
        """
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Filter transcriptions that fit within the highlight timeframe
            relevant_transcriptions = [
                (text, start, end) for text, start, end in transcriptions
                if start >= highlight_start and end <= highlight_end 
            ]
            
            # If no transcriptions fall within the highlight, create a placeholder
            if not relevant_transcriptions:
                logger.warning(f"No transcriptions found for highlight {highlight_start}s to {highlight_end}s")
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"1\n")
                    f.write(f"00:00:01,000 --> 00:00:05,000\n")
                    f.write(f"[Auto-generated caption]\n\n")
                return True
            
            with open(output_file, 'w', encoding='utf-8') as f:
                subtitle_index = 1
                for text, start, end in relevant_transcriptions:
                    # Skip empty text
                    if not text or not text.strip():
                        continue
                        
                    # Format timestamps for SRT (HH:MM:SS,mmm)
                    adjusted_start = start - highlight_start
                    adjusted_end = end - highlight_start
                    
                    # Ensure adjusted times are positive
                    adjusted_start = max(0, adjusted_start)
                    adjusted_end = max(adjusted_start + 0.5, adjusted_end)  # Ensure minimum duration
                    
                    start_str = f"{int(adjusted_start // 3600):02d}:{int((adjusted_start % 3600) // 60):02d}:{int(adjusted_start % 60):02d},{int((adjusted_start % 1) * 1000):03d}"
                    end_str = f"{int(adjusted_end // 3600):02d}:{int((adjusted_end % 3600) // 60):02d}:{int(adjusted_end % 60):02d},{int((adjusted_end % 1) * 1000):03d}"
                    
                    # Wrap long text for vertical video subtitles
                    wrapped_text = textwrap.fill(text, width=40)
                    
                    f.write(f"{subtitle_index}\n")
                    f.write(f"{start_str} --> {end_str}\n")
                    f.write(f"{wrapped_text}\n\n")
                    subtitle_index += 1
                
                # If no subtitles were written, add a placeholder
                if subtitle_index == 1:
                    f.write(f"1\n")
                    f.write(f"00:00:01,000 --> 00:00:05,000\n")
                    f.write(f"[Auto-generated caption]\n\n")
            
            logger.info(f"Created subtitles for highlight {highlight_start}s to {highlight_end}s")
            return True
            
        except Exception as e:
            logger.error(f"Error creating subtitles: {str(e)}", exc_info=True)
            return False
    
    async def create_word_level_timestamps(self, word_level_data, highlight_start, highlight_end, output_file):
        """
        Create a word-level timestamps JSON file for the highlight clip.
        
        Args:
            word_level_data: Dictionary with word-level timestamps
            highlight_start: Start time of the highlight clip
            highlight_end: End time of the highlight clip
            output_file: Path to the output JSON file
            
        Returns:
            bool: True if the file was created successfully, False otherwise
        """
        try:
            # Skip if no word level data
            if not word_level_data:
                logger.warning(f"No word-level timestamps available for highlight {highlight_start}s to {highlight_end}s")
                return False
                
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Create a copy of the data structure for the highlight
            highlight_data = {
                "text": "",
                "segments": []
            }
            
            # Filter and adjust segments that fit within the highlight timeframe
            relevant_segments = []
            for segment in word_level_data.get("segments", []):
                segment_start = segment.get("start", 0)
                segment_end = segment.get("end", 0)
                
                # Skip segments outside the highlight
                if segment_end < highlight_start or segment_start > highlight_end:
                    continue
                
                # Create a copy of the segment with adjusted timestamps
                adjusted_segment = {
                    "id": len(relevant_segments),
                    "start": max(0, segment_start - highlight_start),
                    "end": min(highlight_end - highlight_start, segment_end - highlight_start),
                    "text": segment.get("text", ""),
                    "words": []
                }
                
                # Process and adjust word timestamps
                for word_data in segment.get("words", []):
                    word = word_data.get("word", "")
                    word_start = word_data.get("start", 0)
                    word_end = word_data.get("end", 0)
                    
                    # Skip words outside the highlight
                    if word_end < highlight_start or word_start > highlight_end:
                        continue
                        
                    # Adjust timestamps relative to highlight start
                    adjusted_word = {
                        "word": word,
                        "start": max(0, word_start - highlight_start),
                        "end": min(highlight_end - highlight_start, word_end - highlight_start)
                    }
                    
                    adjusted_segment["words"].append(adjusted_word)
                
                # Only add segments with words
                if adjusted_segment["words"]:
                    relevant_segments.append(adjusted_segment)
            
            # Update the highlight data
            highlight_data["segments"] = relevant_segments
            
            # Combine all text into a single transcript
            highlight_data["text"] = " ".join([s["text"] for s in highlight_data["segments"]])
            
            # Write the JSON file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(highlight_data, f, indent=2)
                
            logger.info(f"Created word-level timestamps for highlight {highlight_start}s to {highlight_end}s")
            return True
            
        except Exception as e:
            logger.error(f"Error creating word-level timestamps: {str(e)}", exc_info=True)
            return False
    
    async def format_transcript(self, transcriptions):
        """
        Format transcriptions for OpenRouter API
        
        Args:
            transcriptions: List of (text, start_time, end_time) tuples
            
        Returns:
            Formatted transcript text
        """
        try:
            if not transcriptions or len(transcriptions) == 0:
                logger.warning("No transcriptions found")
                return ""
            
            # Format transcript for OpenRouter
            transcript_text = ""
            for text, start, end in transcriptions:
                transcript_text += f"{start:.2f} - {end:.2f}: {text}\n"
            
            return transcript_text
            
        except Exception as e:
            logger.error(f"Error formatting transcript: {str(e)}", exc_info=True)
            return ""