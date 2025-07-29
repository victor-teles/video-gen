"""
Test script for faceless video generation
"""
import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from faceless_video_generator import FacelessVideoGenerator

def test_video_generation():
    """Test the complete video generation process"""
    try:
        # Create test processing ID
        processing_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Starting test with processing ID: {processing_id}")
        
        # Initialize generator
        generator = FacelessVideoGenerator(processing_id)
        
        # Test story generation
        logger.info("Testing story generation...")
        story = generator.generate_story(
            story_category="fun_facts",
            story_title="Amazing Space Facts",
            story_description="Fascinating facts about our solar system"
        )
        logger.info(f"Generated story length: {len(story)} characters")
        
        # Test storyboard creation
        logger.info("Testing storyboard creation...")
        scenes = generator.create_storyboard(story)
        logger.info(f"Generated {len(scenes)} scenes")
        
        # Test scene generation
        logger.info("Testing scene generation...")
        for i, scene in enumerate(scenes):
            logger.info(f"Processing scene {i+1}/{len(scenes)}")
            
            # Generate image
            image_url, img_time = generator.generate_scene_image(
                scene['image_prompt'],
                style="cinematic"
            )
            logger.info(f"Generated image in {img_time:.2f}s")
            
            # Download and store image
            image_path = generator.download_and_store_image(image_url, i + 1)
            logger.info(f"Stored image at: {image_path}")
            
            # Generate audio
            audio_path, audio_time = generator.generate_audio(
                scene['text'],
                voice="alloy",
                scene_number=i + 1
            )
            logger.info(f"Generated audio in {audio_time:.2f}s")
            
            # Add paths to scene data
            scene['image_path'] = image_path
            scene['audio_path'] = audio_path
        
        # Test video creation
        logger.info("Testing video creation...")
        video_path, caption_path, file_size = generator.create_video(scenes, story)
        
        # Verify outputs
        logger.info("Verifying outputs...")
        assert Path(video_path).exists(), "Video file not created"
        assert Path(caption_path).exists(), "Caption file not created"
        assert file_size > 0, "Video file is empty"
        
        # Check caption JSON format
        import json
        with open(caption_path, 'r', encoding='utf-8') as f:
            caption_data = json.load(f)
            assert "text" in caption_data, "Caption JSON missing text field"
            assert "segments" in caption_data, "Caption JSON missing segments field"
            for segment in caption_data['segments']:
                assert all(key in segment for key in ['id', 'start', 'end', 'text', 'words']), \
                    "Caption segment missing required fields"
                for word in segment['words']:
                    assert all(key in word for key in ['word', 'start', 'end']), \
                        "Word timing missing required fields"
        
        # Get cost breakdown
        costs = generator.get_cost_breakdown()
        logger.info(f"Total cost: ${costs['total_cost']:.4f}")
        logger.info(f"OpenAI cost: ${costs['openai_cost']:.4f}")
        logger.info(f"Replicate cost: ${costs['replicate_cost']:.4f}")
        
        logger.info("✅ All tests passed successfully!")
        logger.info(f"Video output: {video_path}")
        logger.info(f"Caption output: {caption_path}")
        logger.info(f"File size: {file_size / (1024*1024):.1f}MB")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    test_video_generation() 