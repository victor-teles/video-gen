#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video Clip Generator with Word-Level Captions
=============================================

CLI tool to automatically generate clips from long-form videos with intelligent cropping
and word-level caption files.

Usage:
    python clip_generator.py --input video.mp4 --num-clips 5 --ratio 9:16 --output-dir ./output

Dependencies:
    - clipsai
    - whisperx
    - ultralytics (YOLO)
    - opencv-python
    - torch
    - ffmpeg (system)
"""

import os
import sys
import argparse
import json
import subprocess
import tempfile
import shutil
import gc
from pathlib import Path
import cv2
import numpy as np
import torch
from typing import List, Dict, Tuple, Optional
import re
import traceback

# Import ClipsAI components
try:
    from clipsai import ClipFinder, Transcriber
    print("✓ ClipsAI imported successfully")
except ImportError as e:
    print(f"❌ Error importing ClipsAI: {e}")
    print("Install with: pip install clipsai")
    sys.exit(1)

# Import WhisperX
try:
    import whisperx
    print("✓ WhisperX imported successfully")
except ImportError as e:
    print(f"❌ Error importing WhisperX: {e}")
    print("Install with: pip install git+https://github.com/m-bain/whisperx.git")
    sys.exit(1)

# Import YOLO for auto-cropping
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    print("✓ YOLO imported successfully")
except ImportError as e:
    print(f"⚠️  Warning: YOLO not available: {e}")
    print("Install with: pip install ultralytics")
    YOLO_AVAILABLE = False

# Import storage handler
from storage_handler import StorageHandler

def cleanup_memory():
    """Force garbage collection and clear CUDA cache"""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

class ClipGenerator:
    """Main class for generating video clips with captions"""
    
    def __init__(self, output_dir: str = "./output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize storage handler
        self.storage = StorageHandler()
        
        # Initialize ClipsAI components (lazy loading for memory efficiency)
        self.transcriber = None
        self.clipfinder = None
        
        # Initialize YOLO model if available (lazy loading)
        self.yolo_model = None
        self._yolo_initialized = False
    
    def _init_transcriber(self):
        """Lazy initialization of transcriber"""
        if self.transcriber is None:
            print("🔄 Initializing transcriber...")
            self.transcriber = Transcriber()
            print("✅ Transcriber initialized")
    
    def _init_clipfinder(self):
        """Lazy initialization of clipfinder"""
        if self.clipfinder is None:
            print("🔄 Initializing clipfinder...")
            self.clipfinder = ClipFinder()
            print("✅ Clipfinder initialized")
    
    def _init_yolo(self):
        """Lazy initialization of YOLO model"""
        if YOLO_AVAILABLE and not self._yolo_initialized:
            try:
                print("🔄 Loading YOLO model...")
                self.yolo_model = YOLO("yolov8n.pt")  # Using nano model for memory efficiency
                self._yolo_initialized = True
                print("✅ YOLO model loaded successfully")
            except Exception as e:
                print(f"⚠️  Warning: Could not load YOLO model: {e}")
                self.yolo_model = None
                self._yolo_initialized = True
    
    def extract_high_quality_clip(self, input_file: str, output_file: str, 
                                start_time: float, end_time: float) -> bool:
        """
        Extract a high-quality clip using ffmpeg
        """
        duration = end_time - start_time
        
        cmd = [
            'ffmpeg',
            '-i', input_file,
            '-ss', str(start_time),
            '-t', str(duration),
            '-c:v', 'libx264',      # High-quality H.264 codec
            '-preset', 'slow',       # Slower preset for better quality
            '-crf', '18',           # Constant Rate Factor (visually lossless)
            '-c:a', 'aac',          # AAC audio codec
            '-b:a', '192k',         # Higher bitrate for audio
            '-map_metadata', '-1',   # Remove metadata
            '-y',                   # Overwrite output file
            output_file
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                print(f"❌ Error extracting clip: {stderr.decode()}")
                return False
                
            return True
        except Exception as e:
            print(f"❌ Exception during extraction: {str(e)}")
            return False
    
    def auto_crop_with_yolo(self, input_file: str, output_file: str, 
                           target_ratio: Tuple[int, int]) -> bool:
        """
        Intelligently crop video using YOLO object detection
        """
        # Initialize YOLO if needed
        self._init_yolo()
        
        if not self.yolo_model:
            return self.simple_center_crop(input_file, output_file, target_ratio)
        
        print(f"🎯 Auto-cropping with YOLO to {target_ratio[0]}:{target_ratio[1]} ratio...")
        
        try:
            # Open input video
            cap = cv2.VideoCapture(input_file)
            if not cap.isOpened():
                raise ValueError(f"Could not open video: {input_file}")
            
            # Get video properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Calculate target dimensions
            target_aspect = target_ratio[0] / target_ratio[1]
            current_aspect = width / height
            
            if current_aspect > target_aspect:
                # Video is wider, crop sides
                target_width = int(height * target_aspect)
                target_height = height
            else:
                # Video is taller, crop top/bottom
                target_width = width
                target_height = int(width / target_aspect)
            
            # Sample frames for YOLO detection to determine optimal crop position
            frame_positions = []
            sample_interval = max(1, total_frames // 10)  # Sample 10 frames (reduced for memory efficiency)
            
            for frame_idx in range(0, total_frames, sample_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret:
                    continue
                
                # Run YOLO detection
                results = self.yolo_model(frame, verbose=False, conf=0.3)
                
                # Calculate optimal crop position based on detections
                if len(results[0].boxes) > 0:
                    positions = []
                    weights = []
                    
                    for box in results[0].boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        conf = float(box.conf[0])
                        cls = int(box.cls[0])
                        
                        # Center of detected object
                        center_x = (x1 + x2) / 2
                        
                        # Weight by confidence and object size
                        box_size = (x2 - x1) * (y2 - y1)
                        # Give higher weight to people (class 0)
                        class_weight = 2.0 if cls == 0 else 1.0
                        weight = conf * box_size * class_weight
                        
                        positions.append(center_x)
                        weights.append(weight)
                    
                    if positions:
                        # Weighted average position
                        weighted_center = sum(w * p for w, p in zip(weights, positions)) / sum(weights)
                        x_offset = int(weighted_center - target_width / 2)
                        x_offset = max(0, min(width - target_width, x_offset))
                        frame_positions.append(x_offset)
                
                # Clean up frame from memory after each detection
                del frame, results
                cleanup_memory()
            
            cap.release()
            
            # Final memory cleanup after YOLO processing
            cleanup_memory()
            
            # Calculate final crop position (median of detected positions)
            if frame_positions:
                frame_positions.sort()
                final_x_offset = frame_positions[len(frame_positions) // 2]  # Use median
            else:
                # Fallback to center crop if no detections
                final_x_offset = (width - target_width) // 2
                
            print(f"  🎯 YOLO detected optimal crop position: x={final_x_offset}")
            
            # Apply crop using FFmpeg (much more reliable than OpenCV)
            if current_aspect > target_aspect:
                # Crop sides
                final_y_offset = 0
                crop_filter = f"crop={target_width}:{target_height}:{final_x_offset}:{final_y_offset}"
            else:
                # Crop top/bottom
                final_x_offset = 0
                final_y_offset = (height - target_height) // 2
                crop_filter = f"crop={target_width}:{target_height}:{final_x_offset}:{final_y_offset}"
            
            # Use FFmpeg for cropping (reliable and maintains quality)
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-vf', crop_filter,
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '18',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-y',
                output_file
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            print("✓ Auto-cropping completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error during auto-cropping: {e}")
            return self.simple_center_crop(input_file, output_file, target_ratio)
    
    def simple_center_crop(self, input_file: str, output_file: str, 
                          target_ratio: Tuple[int, int]) -> bool:
        """
        Simple center crop using FFmpeg
        """
        print(f"✂️  Center cropping to {target_ratio[0]}:{target_ratio[1]} ratio...")
        
        try:
            # Get video dimensions
            cap = cv2.VideoCapture(input_file)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
            # Calculate crop dimensions
            target_aspect = target_ratio[0] / target_ratio[1]
            current_aspect = width / height
            
            if current_aspect > target_aspect:
                # Crop sides
                target_width = int(height * target_aspect)
                target_height = height
                x_offset = (width - target_width) // 2
                y_offset = 0
            else:
                # Crop top/bottom
                target_width = width
                target_height = int(width / target_aspect)
                x_offset = 0
                y_offset = (height - target_height) // 2
            
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-vf', f'crop={target_width}:{target_height}:{x_offset}:{y_offset}',
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '18',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-y',
                output_file
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            print("✓ Center cropping completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error during center cropping: {e}")
            return False
    
    def generate_caption_json(self, transcription, clip, clip_text: str) -> Dict:
        """
        Generate word-level caption JSON in the specified format
        """
        clip_start = clip.start_time
        clip_end = clip.end_time
        
        # Get words within the clip time range
        words_in_range = []
        for word in transcription.words:
            if (clip_start <= word.start_time <= clip_end) or \
               (clip_start <= word.end_time <= clip_end) or \
               (word.start_time <= clip_start and word.end_time >= clip_end):
                # Adjust timestamps relative to clip start
                adjusted_word = {
                    "word": word.text,
                    "start": max(0, word.start_time - clip_start),
                    "end": max(0, word.end_time - clip_start)
                }
                words_in_range.append(adjusted_word)
        
        # Break words into segments (approximately every 10-15 words or at natural breaks)
        segments = []
        segment_id = 0
        words_per_segment = 12
        
        for i in range(0, len(words_in_range), words_per_segment):
            segment_words = words_in_range[i:i + words_per_segment]
            if not segment_words:
                continue
                
            segment_start = segment_words[0]["start"]
            segment_end = segment_words[-1]["end"]
            segment_text = " ".join([w["word"] for w in segment_words])
            
            segments.append({
                "id": segment_id,
                "start": segment_start,
                "end": segment_end,
                "text": segment_text,
                "words": segment_words
            })
            segment_id += 1
        
        # Create the JSON structure in the exact format requested
        caption_data = {
            "text": clip_text,
            "segments": segments
        }
        
        return caption_data
    
    def sanitize_filename(self, text: str, max_length: int = 50) -> str:
        """
        Convert text to a safe filename
        """
        # Remove special characters and replace spaces with underscores
        sanitized = re.sub(r'[^\w\s-]', '', text)
        sanitized = re.sub(r'\s+', '_', sanitized)
        
        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        # Remove trailing underscores
        sanitized = sanitized.strip('_')
        
        return sanitized if sanitized else "clip"
    
    def process_video(self, input_video: str, num_clips: int, target_ratio: Tuple[int, int]) -> List[str]:
        """
        Process video to generate clips
        
        Args:
            input_video: Path to input video file
            num_clips: Number of clips to generate
            target_ratio: Target aspect ratio (width, height)
            
        Returns:
            List[str]: List of generated clip filenames
        """
        try:
            # Create temporary working directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                input_path = Path(input_video)
                
                # If input is from S3, download it first
                if self.storage.storage_type == 's3':
                    local_input = temp_dir_path / input_path.name
                    print(f"📥 Downloading input video from S3...")
                    if not self.storage.get_file(input_path, local_input):
                        raise Exception("Failed to download input video from S3")
                    input_video = str(local_input)
                
                # Generate transcription
                print("🎯 Generating transcription...")
                self._init_transcriber()
                transcription = self.transcriber.transcribe(input_video)
                
                # Clean up after transcription
                cleanup_memory()
                
                # Find best clips
                print("🔍 Finding best clips...")
                self._init_clipfinder()
                clips = self.clipfinder.find_clips(
                    transcription,
                    num_clips=num_clips,
                    min_duration=30,
                    max_duration=120
                )
                
                # Clean up after clip finding
                cleanup_memory()
                
                generated_clips = []
                
                # Process each clip
                for i, (clip, clip_text) in enumerate(clips, 1):
                    print(f"\n📽️  Processing clip {i}/{len(clips)}")
            
                    # Create clip filename
                    clip_title = self.sanitize_filename(clip_text)
                    clip_filename = f"clip_{i:02d}_{clip_title}.mp4"
                    caption_filename = f"clip_{i:02d}_{clip_title}.json"
                    
                    # Extract clip to temporary file
                    temp_clip = temp_dir_path / f"temp_clip_{i}.mp4"
                    if not self.extract_high_quality_clip(input_video, str(temp_clip), clip.start, clip.end):
                        print(f"⚠️  Failed to extract clip {i}, skipping...")
                        continue
                    
                    # Auto-crop clip
                    temp_cropped = temp_dir_path / f"temp_cropped_{i}.mp4"
                    if not self.auto_crop_with_yolo(str(temp_clip), str(temp_cropped), target_ratio):
                        print(f"⚠️  Failed to crop clip {i}, skipping...")
                        continue
                    
                    # Generate caption JSON
                    caption_data = self.generate_caption_json(transcription, clip, clip_text)
                    temp_caption = temp_dir_path / f"temp_caption_{i}.json"
                    with open(temp_caption, 'w', encoding='utf-8') as f:
                        json.dump(caption_data, f, indent=2, ensure_ascii=False)
            
                    # Save to final storage location
                    clip_dir = self.output_dir / Path(input_video).stem
                    clip_dir.mkdir(parents=True, exist_ok=True)
                    
                    final_clip = clip_dir / clip_filename
                    final_caption = clip_dir / caption_filename
                    
                    # Save files using storage handler
                    if self.storage.save_file(temp_cropped, final_clip):
                        if self.storage.save_file(temp_caption, final_caption):
                            generated_clips.append(clip_filename)
                            print(f"✅ Saved clip {i}: {clip_filename}")
                            if self.storage.storage_type == 's3':
                                print(f"   📦 Uploaded to S3: {clip_filename}")
                        else:
                            print(f"⚠️  Failed to save caption file for clip {i}")
                    else:
                        print(f"⚠️  Failed to save clip {i}")
                    
                    # Clean up temporary files and memory
                    temp_clip.unlink(missing_ok=True)
                    temp_cropped.unlink(missing_ok=True)
                    temp_caption.unlink(missing_ok=True)
                    
                    # Force memory cleanup after each clip
                    cleanup_memory()
        
                return generated_clips
                
        except Exception as e:
            print(f"❌ Error processing video: {str(e)}")
            traceback.print_exc()
            return []

def parse_ratio(ratio_str: str) -> Tuple[int, int]:
    """Parse ratio string like '9:16' into tuple (9, 16)"""
    try:
        parts = ratio_str.split(':')
        if len(parts) != 2:
            raise ValueError("Ratio must be in format 'width:height' (e.g., '9:16')")
        return (int(parts[0]), int(parts[1]))
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid ratio format: {e}")

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Generate video clips with word-level captions using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python clip_generator.py --input video.mp4 --num-clips 5 --ratio 9:16 --output-dir ./clips
  python clip_generator.py --input podcast.mp4 --num-clips 3 --ratio 1:1 --output-dir ./square_clips
        """
    )
    
    parser.add_argument(
        '--input',
        required=True,
        help='Path to input video file'
    )
    
    parser.add_argument(
        '--num-clips',
        type=int,
        required=True,
        help='Number of clips to generate'
    )
    
    parser.add_argument(
        '--ratio',
        type=parse_ratio,
        required=True,
        help='Target aspect ratio (e.g., 9:16, 1:1, 16:9)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='./output',
        help='Output directory for clips and captions (default: ./output)'
    )
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"❌ Error: Input file not found: {args.input}")
        sys.exit(1)
    
    # Check for required system dependencies
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: ffmpeg not found. Please install ffmpeg first.")
        sys.exit(1)
    
    print("🚀 Video Clip Generator Starting...")
    print("=" * 50)
    
    # Initialize generator
    generator = ClipGenerator(args.output_dir)
    
    # Process video
    try:
        processed_files = generator.process_video(
            args.input,
            args.num_clips,
            args.ratio
        )
        
        print("\n" + "=" * 50)
        if processed_files:
            print(f"✅ SUCCESS! Generated {len(processed_files)} clips:")
            for file_path in processed_files:
                print(f"   📁 {file_path}")
            print(f"\n📂 All files saved to: {args.output_dir}")
        else:
            print("❌ No clips were successfully generated")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 