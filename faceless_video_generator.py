"""
Faceless Video Generator - Core Implementation
Based on SmartClipAI/faceless-video-generator architecture
Adapted to follow existing Video Clip Generator patterns
"""
import openai
import replicate
import json
import os
import time
import tempfile
import requests
import re
import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from datetime import datetime
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, concatenate_videoclips
from moviepy.video.fx.all import resize
from PIL import Image
import math
import gc
import traceback

import config
from storage_handler import StorageHandler

# Configure logging
logger = logging.getLogger(__name__)

def cleanup_memory():
    """Force cleanup of memory to prevent memory leaks"""
    import gc
    gc.collect()
    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip
        VideoFileClip._close_temp_files()  # Close any temp files
    except:
        pass

def cleanup_temp_files(temp_files: List[Path]) -> None:
    """Clean up temporary files"""
    for file in temp_files:
        try:
            if file.exists():
                file.unlink()
        except Exception as e:
            logger.warning(f"Failed to delete temp file {file}: {e}")

def ensure_output_dir(output_dir: Path) -> None:
    """Ensure output directory exists"""
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create output directory {output_dir}: {e}")
        raise

def validate_scene_data(scene: Dict) -> bool:
    """Validate scene data has required fields"""
    required_fields = ['scene_number', 'text', 'image_prompt', 
                      'start_time', 'end_time', 'duration',
                      'image_path', 'audio_path']
    return all(field in scene for field in required_fields)

def get_safe_filename(filename: str) -> str:
    """Convert string to safe filename"""
    import re
    # Remove invalid chars
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Remove control characters
    filename = "".join(char for char in filename if ord(char) >= 32)
    return filename

class VideoGenerationError(Exception):
    """Custom exception for video generation errors"""
    pass

class FacelessVideoGenerator:
    """Main class for generating faceless videos following SmartClipAI architecture"""
    
    def __init__(self, processing_id: str):
        """Initialize generator with processing ID for storage paths"""
        self.processing_id = processing_id
        
        # Initialize OpenAI client
        self.openai_client = openai.OpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL
        )
        
        # Initialize Replicate (will be set when needed)
        if config.REPLICATE_API_TOKEN:
            os.environ["REPLICATE_API_TOKEN"] = config.REPLICATE_API_TOKEN
        
        # Initialize storage handler (following existing pattern)
        self.storage = StorageHandler()
        
        # Cost tracking
        self.total_cost = 0.0
        self.openai_cost = 0.0
        self.replicate_cost = 0.0
        
        # Set output directory
        if config.STORAGE_TYPE == 's3':
            self.output_dir = Path(tempfile.mkdtemp())
        else:
            self.output_dir = config.FACELESS_VIDEOS_DIR / self.processing_id
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Storage paths (following existing pattern)
        self.temp_dir = None
        self.scenes_data = []
    
    def generate_story(self, story_category: str, story_content: str = None, 
                      story_title: str = "", story_description: str = "") -> str:
        """Generate story based on category and user input (SmartClipAI approach)"""
        
        if story_category == "custom" and story_content:
            # Use user-provided content with some enhancement if title/description provided
            if story_title or story_description:
                enhancement_prompt = f"""
                Enhance this story content for a faceless video format. Make it more engaging and suitable for visual storytelling.
                
                Title: {story_title}
                Description: {story_description}
                Content: {story_content}
                
                Return the enhanced story content only (no titles or descriptions).
                Target length: {config.STORY_CHAR_LIMIT_MIN}-{config.STORY_CHAR_LIMIT_MAX} characters.
                """
                
                response = self.openai_client.chat.completions.create(
                    model=config.STORY_MODEL,
                    messages=[{"role": "user", "content": enhancement_prompt}],
                    temperature=0.7,
                    max_tokens=1000
                )
                
                # Track cost
                token_cost = response.usage.total_tokens * config.OPENAI_COST_PER_TOKEN
                self.openai_cost += token_cost
                self.total_cost += token_cost
                
                return response.choices[0].message.content
            
            return story_content
        
        # Story generation prompts (based on SmartClipAI)
        story_prompts = {
            "scary": f"""Create a spine-chilling horror story perfect for a faceless video format. 
                    The story should build tension gradually with atmospheric descriptions and psychological elements.
                    Include vivid, disturbing imagery that can be visualized in scenes.
                    Title context: {story_title}
                    Description context: {story_description}
                    Target length: {config.STORY_CHAR_LIMIT_MIN}-{config.STORY_CHAR_LIMIT_MAX} characters.
                    Make it suitable for visual storytelling with clear scene breaks.""",
            
            "mystery": f"""Write an intriguing mystery story with unexpected twists perfect for visual storytelling.
                      Include clues, red herrings, and a surprising revelation.
                      Focus on creating suspense and curiosity with clear visual scenes.
                      Title context: {story_title}
                      Description context: {story_description}
                      Target length: {config.STORY_CHAR_LIMIT_MIN}-{config.STORY_CHAR_LIMIT_MAX} characters.""",
            
            "bedtime": f"""Create a calming bedtime story with gentle imagery and soothing themes.
                      Include magical or nature-based elements that promote relaxation.
                      The tone should be warm and comforting with beautiful visual scenes.
                      Title context: {story_title}
                      Description context: {story_description}
                      Target length: {config.STORY_CHAR_LIMIT_MIN}-{config.STORY_CHAR_LIMIT_MAX} characters.""",
            
            "history": f"""Tell a fascinating historical story about an interesting event, person, or discovery.
                      Include accurate historical details and make it educational yet entertaining.
                      Focus on lesser-known facts with strong visual elements.
                      Title context: {story_title}
                      Description context: {story_description}
                      Target length: {config.STORY_CHAR_LIMIT_MIN}-{config.STORY_CHAR_LIMIT_MAX} characters.""",
            
            "motivational": f"""Write an inspiring motivational story about overcoming challenges.
                           Include real-world lessons and actionable insights.
                           The tone should be uplifting and empowering with inspirational visuals.
                           Title context: {story_title}
                           Description context: {story_description}
                           Target length: {config.STORY_CHAR_LIMIT_MIN}-{config.STORY_CHAR_LIMIT_MAX} characters.""",
            
            "fun_facts": f"""Create a collection of amazing, mind-blowing fun facts that will surprise viewers.
                          Include scientific discoveries, nature phenomena, or historical curiosities.
                          Make each fact engaging and memorable with strong visual potential.
                          Title context: {story_title}
                          Description context: {story_description}
                          Target length: {config.STORY_CHAR_LIMIT_MIN}-{config.STORY_CHAR_LIMIT_MAX} characters."""
        }
        
        prompt = story_prompts.get(story_category, story_prompts["fun_facts"])
        
        try:
            response = self.openai_client.chat.completions.create(
                model=config.STORY_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=config.STORY_TEMPERATURE,
                max_tokens=1000
            )
            
            story = response.choices[0].message.content
            
            # Track cost
            token_cost = response.usage.total_tokens * config.OPENAI_COST_PER_TOKEN
            self.openai_cost += token_cost
            self.total_cost += token_cost
            
            return story
            
        except Exception as e:
            raise Exception(f"Story generation failed: {str(e)}")
    
    def create_storyboard(self, story: str) -> List[Dict]:
        """Break story into scenes with image prompts (SmartClipAI methodology)"""
        storyboard_prompt = f"""
        You are a professional video storyboard creator. Break this story into exactly {config.MAX_SCENES} visual scenes for a faceless video.
        
        For each scene, provide:
        1. "text": The narrator voiceover text (what will be spoken)
        2. "image_prompt": Detailed visual description for AI image generation (be very descriptive and cinematic)
        3. "duration": Estimated duration in seconds based on text length (3-8 seconds per scene)
        
        Guidelines:
        - Each scene should have natural speech flow
        - Image prompts should be cinematic and visually striking
        - Text should be clear and engaging when spoken
        - Maintain visual consistency throughout
        - Make images suitable for {config.IMAGE_ASPECT_RATIO} aspect ratio
        - Focus on visual storytelling
        
        Story to break down:
        {story}
        
        Return ONLY a valid JSON array in this exact format:
        [
            {{
                "text": "Scene narration text here",
                "image_prompt": "Detailed visual description for AI generation",
                "duration": 5.2
            }},
            ...
        ]
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model=config.STORY_MODEL,
                messages=[{"role": "user", "content": storyboard_prompt}],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Track cost
            token_cost = response.usage.total_tokens * config.OPENAI_COST_PER_TOKEN
            self.openai_cost += token_cost
            self.total_cost += token_cost
            
            # Parse JSON response
            storyboard_text = response.choices[0].message.content
            
            # Clean up response (remove markdown formatting if present)
            if "```json" in storyboard_text:
                storyboard_text = storyboard_text.split("```json")[1].split("```")[0]
            elif "```" in storyboard_text:
                storyboard_text = storyboard_text.split("```")[1].split("```")[0]
            
            scenes = json.loads(storyboard_text.strip())
            
            # Validate and fix scene data (following existing pattern)
            current_time = 0.0
            for i, scene in enumerate(scenes):
                if "duration" not in scene:
                    # Estimate duration based on text length (average speaking rate)
                    word_count = len(scene["text"].split())
                    scene["duration"] = max(3.0, word_count * 0.4)  # ~150 WPM
                
                scene["start_time"] = current_time
                scene["end_time"] = current_time + scene["duration"]
                current_time += scene["duration"]
                scene["scene_number"] = i + 1
            
            return scenes
            
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse storyboard JSON: {str(e)}")
        except Exception as e:
            raise Exception(f"Storyboard creation failed: {str(e)}")
    
    def generate_scene_image(self, image_prompt: str, style: str) -> Tuple[str, float]:
        """Generate image for scene using Replicate (SmartClipAI approach)"""
        
        # Style-specific prompt enhancements
        style_prompts = {
            "photorealistic": "ultra-realistic, high resolution, professional photography, detailed",
            "cinematic": "cinematic lighting, dramatic composition, film quality, movie scene",
            "anime": "anime style, vibrant colors, detailed illustration, Japanese animation",
            "comic-book": "comic book art style, bold lines, dramatic colors, graphic novel",
            "pixar-art": "3D Pixar animation style, colorful, family-friendly, animated movie"
        }
        
        enhanced_prompt = f"{image_prompt}, {style_prompts.get(style, style)} style, {config.IMAGE_ASPECT_RATIO} aspect ratio, high quality, detailed"
        
        try:
            start_time = time.time()
            
            # Generate image using Replicate
            output = replicate.run(
                config.IMAGE_MODEL,
                input={
                    "prompt": enhanced_prompt,
                    "aspect_ratio": config.IMAGE_ASPECT_RATIO,
                    "num_inference_steps": config.IMAGE_INFERENCE_STEPS,
                    "guidance": config.IMAGE_GUIDANCE,
                    "output_quality": config.IMAGE_QUALITY,
                    "disable_safety_checker": False
                }
            )
            
            generation_time = time.time() - start_time
            
            # Track cost
            self.replicate_cost += config.REPLICATE_COST_PER_IMAGE
            self.total_cost += config.REPLICATE_COST_PER_IMAGE
            
            if isinstance(output, list) and output:
                image_url = output[0]
            else:
                image_url = str(output)
            
            return image_url, generation_time
            
        except Exception as e:
            raise Exception(f"Image generation failed: {str(e)}")
    
    def download_and_store_image(self, image_url: str, scene_number: int) -> str:
        """Download image from URL and store it (following existing storage pattern)"""
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Create filename following existing pattern
            filename = f"scene_{self.processing_id}_{scene_number:02d}.png"
            
            # Create temp file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_file.write(response.content)
            temp_file.close()
            
            # Storage path following existing pattern
            if config.STORAGE_TYPE == 's3':
                storage_path = f"results/faceless-videos/{filename}"
            else:
                storage_path = config.FACELESS_VIDEOS_DIR / self.processing_id / filename
                os.makedirs(storage_path.parent, exist_ok=True)
            
            # Save using existing storage handler
            if self.storage.save_file(temp_file.name, storage_path):
                os.unlink(temp_file.name)  # Clean up temp file
                return str(storage_path)
            else:
                raise Exception("Failed to store image")
                
        except Exception as e:
            raise Exception(f"Image download/storage failed: {str(e)}")
    
    def generate_audio(self, text: str, voice: str, scene_number: int) -> Tuple[str, float]:
        """Generate TTS audio using OpenAI (SmartClipAI approach)"""
        try:
            start_time = time.time()
            
            response = self.openai_client.audio.speech.create(
                model=config.TTS_MODEL,
                voice=voice,
                input=text,
                speed=config.TTS_SPEECH_RATE
            )
            
            generation_time = time.time() - start_time
            
            # Track cost
            tts_cost = len(text) * config.OPENAI_TTS_COST_PER_CHAR
            self.openai_cost += tts_cost
            self.total_cost += tts_cost
            
            # Create filename following existing pattern
            filename = f"audio_{self.processing_id}_{scene_number:02d}.mp3"
            
            # Save to temp file first
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_file.close()  # Close file handle before writing
            response.stream_to_file(temp_file.name)
            
            # Storage path following existing pattern
            if config.STORAGE_TYPE == 's3':
                storage_path = f"results/faceless-videos/{filename}"
            else:
                storage_path = config.FACELESS_VIDEOS_DIR / self.processing_id / filename
                os.makedirs(storage_path.parent, exist_ok=True)
            
            # Save using existing storage handler
            success = self.storage.save_file(temp_file.name, storage_path)
            
            try:
                # Clean up temp file
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
            except Exception as cleanup_error:
                print(f"Warning: Failed to clean up temp audio file: {cleanup_error}")
            
            if success:
                return str(storage_path), generation_time
            else:
                raise Exception("Failed to store audio")
            
        except Exception as e:
            raise Exception(f"Audio generation failed: {str(e)}")
    
    def generate_caption_json(self, scenes: List[Dict], story_text: str) -> Dict:
        """Generate word-level caption JSON with accurate timing from TTS audio"""
        try:
            # Import transcription modules 
            from clip_generator import ClipGenerator
            import tempfile
            from moviepy.editor import AudioFileClip, concatenate_audioclips
            
            print("📝 Generating accurate captions from TTS audio...")
            
            # Step 1: Concatenate all audio files to create full audio track
            audio_clips = []
            temp_files = []
            
            for scene in scenes:
                if 'audio_path' in scene and scene['audio_path']:
                    try:
                        audio_clip = AudioFileClip(str(scene['audio_path']))
                        audio_clips.append(audio_clip)
                    except Exception as e:
                        print(f"Warning: Failed to load audio for scene {scene.get('scene_number', '?')}: {e}")
                        continue
            
            if not audio_clips:
                print("Warning: No audio clips found, falling back to estimated timing")
                return self._generate_fallback_captions(scenes, story_text)
            
            # Create concatenated audio file
            full_audio = concatenate_audioclips(audio_clips)
            
            # Save to temporary file for transcription
            temp_audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            temp_audio_path = temp_audio_file.name
            temp_audio_file.close()
            temp_files.append(Path(temp_audio_path))
            
            full_audio.write_audiofile(temp_audio_path, verbose=False, logger=None)
            
            # Step 2: Use WhisperX to transcribe the concatenated audio
            print("🎯 Transcribing TTS audio for precise word timing...")
            
            # Initialize transcriber (reuse clip generator's transcriber)
            clip_gen = ClipGenerator(str(self.output_dir))
            clip_gen._init_transcriber()
            
            # Transcribe the full audio
            transcription = clip_gen.transcriber.transcribe(audio_file_path=temp_audio_path)
            
            # Step 3: Map transcribed words back to scenes
            segments = []
            segment_id = 0
            current_scene_time = 0.0
            
            # Combine all scene texts for reference
            full_text_words = []
            scene_word_boundaries = []  # Track which words belong to which scene
            
            for scene in scenes:
                scene_words = scene["text"].split()
                scene_start_idx = len(full_text_words)
                full_text_words.extend(scene_words)
                scene_end_idx = len(full_text_words) - 1
                scene_word_boundaries.append({
                    'scene_number': scene.get('scene_number', len(scene_word_boundaries) + 1),
                    'scene_text': scene["text"],
                    'start_word_idx': scene_start_idx,
                    'end_word_idx': scene_end_idx,
                    'expected_start_time': current_scene_time,
                    'expected_duration': scene.get('duration', 5.0)
                })
                current_scene_time += scene.get('duration', 5.0)
            
            # Map transcribed words to scenes
            transcribed_words = transcription.words if hasattr(transcription, 'words') else []
            
            # Improved word mapping strategy
            if len(transcribed_words) > 0:
                # Strategy 1: Try direct position mapping first
                total_expected_words = len(full_text_words)
                total_transcribed_words = len(transcribed_words)
                
                print(f"📊 Mapping {total_transcribed_words} transcribed words to {total_expected_words} expected words")
                
                for scene_info in scene_word_boundaries:
                    scene_start_idx = scene_info['start_word_idx']
                    scene_end_idx = scene_info['end_word_idx']
                    scene_text = scene_info['scene_text']
                    expected_word_count = scene_end_idx - scene_start_idx + 1
                    
                    scene_transcribed_words = []
                    
                    # Calculate proportional mapping
                    if total_expected_words > 0 and total_transcribed_words > 0:
                        # Map scene word indices to transcribed word indices proportionally
                        start_ratio = scene_start_idx / total_expected_words
                        end_ratio = (scene_end_idx + 1) / total_expected_words
                        
                        transcribed_start_idx = int(start_ratio * total_transcribed_words)
                        transcribed_end_idx = int(end_ratio * total_transcribed_words)
                        
                        # Ensure we don't go out of bounds
                        transcribed_start_idx = max(0, min(transcribed_start_idx, total_transcribed_words - 1))
                        transcribed_end_idx = max(transcribed_start_idx + 1, min(transcribed_end_idx, total_transcribed_words))
                        
                        # Extract words for this scene
                        for i in range(transcribed_start_idx, transcribed_end_idx):
                            if i < len(transcribed_words):
                                word_data = transcribed_words[i]
                                scene_transcribed_words.append({
                                    "word": word_data.text.strip(),
                                    "start": round(word_data.start_time, 3),
                                    "end": round(word_data.end_time, 3)
                                })
                        
                        print(f"Scene {scene_info['scene_number']}: Mapped {len(scene_transcribed_words)} words (expected {expected_word_count})")
                    
                    # Fallback if proportional mapping failed or gave no words
                    if not scene_transcribed_words:
                        print(f"⚠️  Fallback timing for scene {scene_info['scene_number']}")
                        scene_words = scene_text.split()
                        scene_duration = scene_info['expected_duration']
                        word_duration = scene_duration / len(scene_words) if scene_words else 0
                        scene_start_time = scene_info['expected_start_time']
                        
                        for j, word in enumerate(scene_words):
                            word_start = scene_start_time + (j * word_duration)
                            word_end = word_start + word_duration
                            scene_transcribed_words.append({
                                "word": word.strip(),
                                "start": round(word_start, 3),
                                "end": round(word_end, 3)
                            })
                    
                    if scene_transcribed_words:
                        # Create segment for this scene
                        segment_start = scene_transcribed_words[0]["start"]
                        segment_end = scene_transcribed_words[-1]["end"]
                        
                        segments.append({
                            "id": segment_id,
                            "start": segment_start,
                            "end": segment_end,
                            "text": scene_text,
                            "words": scene_transcribed_words
                        })
                        segment_id += 1
            
            else:
                print("⚠️  No transcribed words found, using fallback timing for all scenes")
                # Complete fallback to estimated timing
                for scene_info in scene_word_boundaries:
                    scene_text = scene_info['scene_text']
                    scene_words = scene_text.split()
                    scene_duration = scene_info['expected_duration']
                    word_duration = scene_duration / len(scene_words) if scene_words else 0
                    scene_start_time = scene_info['expected_start_time']
                    
                    words_data = []
                    for j, word in enumerate(scene_words):
                        word_start = scene_start_time + (j * word_duration)
                        word_end = word_start + word_duration
                        words_data.append({
                            "word": word.strip(),
                            "start": round(word_start, 3),
                            "end": round(word_end, 3)
                        })
                    
                    segments.append({
                        "id": segment_id,
                        "start": scene_start_time,
                        "end": scene_start_time + scene_duration,
                        "text": scene_text,
                        "words": words_data
                    })
                    segment_id += 1
            
            # Create the final caption structure
            full_text = " ".join([scene["text"] for scene in scenes])
            
            caption_data = {
                "text": full_text,
                "segments": segments
            }
            
            print(f"✅ Generated {len(segments)} caption segments with precise timing")
            
            # Cleanup
            for clip in audio_clips:
                try:
                    clip.close()
                except:
                    pass
            try:
                full_audio.close()
            except:
                pass
            
            # Clean up temp files
            for temp_file in temp_files:
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                except Exception as e:
                    print(f"Warning: Failed to clean up temp file {temp_file}: {e}")
            
            return caption_data
            
        except Exception as e:
            print(f"⚠️  Transcription-based caption generation failed: {e}")
            print("📝 Falling back to estimated timing...")
            return self._generate_fallback_captions(scenes, story_text)
    
    def _generate_fallback_captions(self, scenes: List[Dict], story_text: str) -> Dict:
        """Fallback method for caption generation when transcription fails"""
        full_text = " ".join([scene["text"] for scene in scenes])
        segments = []
        
        for i, scene in enumerate(scenes):
            # Calculate word timings within scene (original logic)
            scene_words = scene["text"].split()
            scene_duration = scene.get("duration", 5.0)
            word_duration = scene_duration / len(scene_words) if scene_words else 0
            
            words_data = []
            for j, word in enumerate(scene_words):
                word_start = scene.get("start_time", 0) + (j * word_duration)
                word_end = word_start + word_duration
                words_data.append({
                    "word": word,
                    "start": round(word_start, 3),
                    "end": round(word_end, 3)
                })
            
            segments.append({
                "id": i,
                "start": scene.get("start_time", 0),
                "end": scene.get("end_time", scene_duration),
                "text": scene["text"],
                "words": words_data
            })
        
        return {
            "text": full_text,
            "segments": segments
        }
    
    def create_video(self, scenes: List[Dict], story: str) -> Tuple[Path, Path, int]:
        """Create the final video by combining all scenes with transitions"""
        temp_files = []  # Track temp files for cleanup
        clips = []  # Track clips for cleanup
        
        try:
            # Ensure output directory exists
            ensure_output_dir(self.output_dir)
            
            # Validate scenes
            valid_scenes = [s for s in scenes if validate_scene_data(s)]
            if not valid_scenes:
                raise VideoGenerationError("No valid scenes found")

            # STEP 1: Update scene timing with actual audio durations
            print("🎵 Calculating actual scene timing from audio files...")
            current_time = 0.0
            
            for i, scene in enumerate(valid_scenes):
                try:
                    # Load audio to get actual duration
                    if 'audio_path' in scene and scene['audio_path']:
                        from moviepy.editor import AudioFileClip
                        audio_clip = AudioFileClip(str(scene['audio_path']))
                        actual_duration = audio_clip.duration
                        audio_clip.close()  # Clean up immediately
                        
                        # Update scene with actual timing
                        scene['start_time'] = current_time
                        scene['end_time'] = current_time + actual_duration
                        scene['duration'] = actual_duration
                        current_time += actual_duration
                        
                        print(f"Scene {i+1}: {actual_duration:.2f}s (actual) vs {scene.get('estimated_duration', 'N/A')}s (estimated)")
                    else:
                        # Fallback to estimated duration if no audio
                        estimated_duration = scene.get('duration', 5.0)
                        scene['start_time'] = current_time
                        scene['end_time'] = current_time + estimated_duration
                        scene['duration'] = estimated_duration
                        current_time += estimated_duration
                        print(f"Scene {i+1}: Using estimated duration {estimated_duration:.2f}s")
                        
                except Exception as e:
                    print(f"Warning: Failed to get duration for scene {i+1}: {e}")
                    # Use estimated duration as fallback
                    estimated_duration = scene.get('duration', 5.0)
                    scene['start_time'] = current_time
                    scene['end_time'] = current_time + estimated_duration
                    scene['duration'] = estimated_duration
                    current_time += estimated_duration

            # Parse target aspect ratio
            try:
                ratio_parts = config.IMAGE_ASPECT_RATIO.split(':')
                target_ratio = (int(ratio_parts[0]), int(ratio_parts[1]))
            except:
                raise VideoGenerationError(f"Invalid aspect ratio: {config.IMAGE_ASPECT_RATIO}")
            
            # Calculate target dimensions based on aspect ratio
            if target_ratio[0] == 9 and target_ratio[1] == 16:  # Portrait (9:16)
                target_width = 1080
                target_height = 1920
            elif target_ratio[0] == 16 and target_ratio[1] == 9:  # Landscape (16:9)
                target_width = 1920
                target_height = 1080
            elif target_ratio[0] == 1 and target_ratio[1] == 1:  # Square (1:1)
                target_width = 1080
                target_height = 1080
            else:  # Default to 1080p equivalent
                if target_ratio[1] > target_ratio[0]:  # Taller than wide
                    target_height = 1920
                    target_width = int(1920 * target_ratio[0] / target_ratio[1])
                    # Ensure width is even (required for some codecs)
                    target_width = (target_width // 2) * 2
                else:  # Wider than tall
                    target_width = 1920
                    target_height = int(1920 * target_ratio[1] / target_ratio[0])
                    # Ensure height is even (required for some codecs)
                    target_height = (target_height // 2) * 2

            # STEP 2: Create video clips using actual durations
            print("🎬 Creating video clips...")
            for i, scene in enumerate(valid_scenes):
                try:
                    # Load image
                    img = Image.open(scene['image_path'])
                    width, height = img.size
                    
                    # Calculate resize dimensions while maintaining aspect ratio
                    scale_width = target_width / width
                    scale_height = target_height / height
                    scale = max(scale_width, scale_height)  # Scale to fill target dimensions
                    
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    
                    # Resize image
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # Crop to target dimensions from center
                    left = (new_width - target_width) // 2
                    top = (new_height - target_height) // 2
                    right = left + target_width
                    bottom = top + target_height
                    
                    img = img.crop((left, top, right, bottom))
                    
                    # Save temporary resized image
                    temp_path = Path(scene['image_path']).parent / f"resized_{i}.png"
                    img.save(temp_path)
                    temp_files.append(temp_path)
                    
                    # Create video clip from resized image
                    img_clip = ImageClip(str(temp_path))
                    
                    # Load audio
                    audio_clip = AudioFileClip(str(scene['audio_path']))
                    actual_duration = audio_clip.duration
                    
                    # Set clip duration and add audio
                    img_clip = img_clip.set_duration(actual_duration)
                    img_clip = img_clip.set_audio(audio_clip)
                    
                    # Add zoom effect
                    zoom_factor = 1.1
                    img_clip = img_clip.fx(
                        resize, 
                        lambda t: zoom_factor + (1-zoom_factor)*t/actual_duration
                    )
                    
                    clips.append(img_clip)
                    
                except Exception as e:
                    logger.error(f"Failed to process scene {i}: {e}")
                    continue
            
            if not clips:
                raise Exception("No valid clips were created")
            
            # Add crossfade transitions
            final_clips = []
            for i, clip in enumerate(clips):
                if i > 0:
                    # Add crossfade to all clips except the first
                    clip = clip.crossfadein(1.0)
                final_clips.append(clip)
            
            # Concatenate all clips
            final_video = concatenate_videoclips(final_clips, method="compose")
            
            # Generate output paths
            video_filename = get_safe_filename(f"{self.processing_id}_final.mp4")
            caption_filename = get_safe_filename(f"{self.processing_id}_captions.json")
            
            video_path = self.output_dir / video_filename
            caption_path = self.output_dir / caption_filename
            
            # Write video file
            final_video.write_videofile(
                str(video_path),
                fps=30,
                codec='libx264',
                audio_codec='aac',
                preset='medium',
                threads=4,
                logger=None,
                # Force exact dimensions
                ffmpeg_params=[
                    '-vf', f'scale={target_width}:{target_height}:force_original_aspect_ratio=decrease',
                    '-c:v', 'libx264',
                    '-pix_fmt', 'yuv420p'  # Ensure compatibility
                ]
            )

            # STEP 3: Generate word-level caption JSON with accurate timing
            print("📝 Generating accurate captions with actual timing...")
            caption_data = self.generate_caption_json(valid_scenes, story)
            with open(caption_path, 'w', encoding='utf-8') as f:
                json.dump(caption_data, f, indent=2, ensure_ascii=False)
            
            # Get file size
            file_size = video_path.stat().st_size
            
            total_duration = sum(scene['duration'] for scene in valid_scenes)
            print(f"✅ Video created: {total_duration:.2f}s total duration")
            
            return video_path, caption_path, file_size
            
        except Exception as e:
            logger.error(f"Failed to create video: {e}\n{traceback.format_exc()}")
            raise VideoGenerationError(f"Video creation failed: {str(e)}")
        finally:
            # Clean up clips
            for clip in clips:
                try:
                    clip.close()
                except:
                    pass
            
            # Clean up temp files
            cleanup_temp_files(temp_files)
            cleanup_memory()
    
    def _generate_captions(self, scenes: List[Dict], caption_path: Path) -> None:
        """Generate SRT caption file from scenes"""
        with open(caption_path, 'w', encoding='utf-8') as f:
            current_time = 0
            for i, scene in enumerate(scenes):
                start_time = self._format_srt_time(current_time)
                end_time = self._format_srt_time(current_time + scene['duration'])
                
                f.write(f"{i+1}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{scene['text']}\n\n")
                
                current_time += scene['duration']
                
    def _format_srt_time(self, seconds: float) -> str:
        """Format time in seconds to SRT timestamp format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds % 1) * 1000)
        seconds = int(seconds)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def get_cost_breakdown(self) -> Dict:
        """Get detailed cost breakdown"""
        return {
            "openai_cost": round(self.openai_cost, 4),
            "replicate_cost": round(self.replicate_cost, 4),
            "total_cost": round(self.total_cost, 4)
        }