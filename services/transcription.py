"""
Transcription service for audio files
Adapted from backend2 for use with backend architecture
"""
import os
import warnings
import logging
import json

# Use backend's config module
import config

# Initialize logger
logger = logging.getLogger(__name__)

# Suppress warnings
warnings.filterwarnings("ignore")

class TranscriptionService:
    """Service for transcribing audio files"""
    
    def __init__(self):
        """Initialize the transcription service"""
        self.whisperx_available = False
        self.faster_whisper_available = False
        self.model = None
        self.model_a = None
        self.metadata = None
        
        # Check for WhisperX
        try:
            import whisperx
            import torch
            
            # Use backend configuration
            device = config.AI_DEVICE if hasattr(config, 'AI_DEVICE') else "cpu"
            if device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"
            
            model_size = config.WHISPER_MODEL_SIZE
            compute_type = "float16" if device == "cuda" else "int8"
            
            logger.info(f"Loading WhisperX {model_size} model on {device} with {compute_type} compute type...")
            self.model = whisperx.load_model(model_size, device, compute_type=compute_type)
            
            logger.info("Loading alignment model...")
            self.model_a, self.metadata = whisperx.load_align_model(language_code="en", device=device)
            
            self.whisperx_available = True
            logger.info("WhisperX is available with models loaded")
        except Exception as e:
            logger.warning(f"WhisperX is not available: {str(e)}")
            
            # Try Faster Whisper as fallback
            try:
                from faster_whisper import WhisperModel
                self.faster_whisper_available = True
                logger.info("Faster Whisper is available")
            except ImportError:
                logger.warning("Faster Whisper is not available")

    async def transcribe_audio(self, audio_path):
        """
        Transcribe audio using WhisperX or Faster Whisper
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Tuple of:
             - List of transcriptions with [text, start, end] format
             - Dictionary with word-level timestamps (if available)
        """
        try:
            # Get the absolute path of the audio file
            abs_audio_path = os.path.abspath(audio_path)
            logger.info(f"Transcribing audio: {abs_audio_path}")
            
            # Try WhisperX first
            if self.whisperx_available:
                return await self._transcribe_with_whisperx(abs_audio_path)
            
            # Fall back to Faster Whisper
            elif self.faster_whisper_available:
                transcriptions = await self._transcribe_with_faster_whisper(abs_audio_path)
                return transcriptions, None  # No word-level timestamps with Faster Whisper
            
            # No transcription service available
            else:
                logger.error("No transcription service available")
                return [], None
                
        except Exception as e:
            logger.error(f"Transcription Error: {str(e)}", exc_info=True)
            return [], None

    async def _transcribe_with_whisperx(self, audio_path):
        """
        Transcribe using WhisperX
        
        Returns:
            Tuple of:
             - List of transcriptions with [text, start, end] format
             - Dictionary with word-level timestamps 
        """
        try:
            import whisperx
            import torch
            
            # 1. Transcribe with base Whisper using pre-loaded model
            logger.info("Transcribing with WhisperX...")
            result = self.model.transcribe(audio_path, language="en")
            
            # 2. Align the segments using pre-loaded alignment model
            logger.info("Aligning segments...")
            result = whisperx.align(result["segments"], self.model_a, self.metadata, audio_path, 
                                   device=config.AI_DEVICE if hasattr(config, 'AI_DEVICE') else "cpu")
            
            # 3. Process results and preserve word-level timestamps
            transcriptions = []
            word_level_data = {
                "text": "",
                "segments": []
            }
            
            for segment in result["segments"]:
                text = segment["text"].strip()
                start = segment["start"]
                end = segment["end"]
                transcriptions.append([text, start, end])
                
                # Add to word-level data structure
                segment_data = {
                    "id": len(word_level_data["segments"]),
                    "start": start,
                    "end": end,
                    "text": text,
                    "words": []
                }
                
                # Process word-level timestamps if available
                if "words" in segment:
                    for word_data in segment["words"]:
                        word = word_data.get("word", "").strip()
                        word_start = word_data.get("start", 0)
                        word_end = word_data.get("end", 0)
                        
                        # Add to segment's words
                        if word:  # Skip empty words
                            segment_data["words"].append({
                                "word": word,
                                "start": word_start,
                                "end": word_end
                            })
                
                word_level_data["segments"].append(segment_data)
            
            # Combine all text into a single transcript
            word_level_data["text"] = " ".join([s["text"] for s in word_level_data["segments"]])
            
            logger.info(f"Transcription complete! Found {len(transcriptions)} segments with word-level timestamps.")
            
            # Save word-level data to JSON file for debugging/reference
            json_path = os.path.splitext(audio_path)[0] + "_transcript.json"
            try:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(word_level_data, f, indent=2)
                logger.info(f"Saved word-level transcript to {json_path}")
            except Exception as e:
                logger.warning(f"Failed to save word-level transcript JSON: {str(e)}")
            
            return transcriptions, word_level_data
            
        except Exception as e:
            logger.error(f"WhisperX processing error: {str(e)}", exc_info=True)
            return [], None

    async def _transcribe_with_faster_whisper(self, audio_path):
        """Transcribe using Faster Whisper"""
        try:
            from faster_whisper import WhisperModel
            
            # Use backend configuration
            model_size = config.WHISPER_MODEL_SIZE
            logger.info(f"Loading Faster Whisper {model_size} model...")
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            
            # Transcribe
            segments, info = model.transcribe(audio_path, beam_size=5, language="en")
            
            # Process results
            transcriptions = []
            for segment in segments:
                text = segment.text.strip()
                start = segment.start
                end = segment.end
                transcriptions.append([text, start, end])
            
            logger.info(f"Transcription complete! Found {len(transcriptions)} segments.")
            return transcriptions
            
        except Exception as e:
            logger.error(f"Faster Whisper processing error: {str(e)}", exc_info=True)
            return []