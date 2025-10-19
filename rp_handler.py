import runpod
import time  
import tempfile
from pathlib import Path
from storage_handler import StorageHandler
from services.video_service import VideoService
import logging
import os

logger = logging.getLogger(__name__)

async def handler(event):
#   This function processes incoming requests to your Serverless endpoint.
#
#    Args:
#        event (dict): Contains the input data and request metadata
#       
#    Returns:
#       Any: The result to be returned to the client
    
    # Extract input data
    print(f"Worker Start")
    input = event['input']
    
    filename = input.get('filename')  
    num_clips = input.get('num_clips', 3)  

    storage = StorageHandler()

    temp_input_file = tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix)
    temp_input_file.close()
    
    source_path = f"uploads/{filename}"
    
    if not storage.get_file(source_path, temp_input_file.name):
        raise FileNotFoundError(f"Failed to download file from S3: {source_path}")
    
    input_file = Path(temp_input_file.name)
    
    video_service = VideoService()
    
    # Force memory cleanup before processing
    import gc
    gc.collect()
    
    try:
        result = await video_service.process_video(
            video_path=str(input_file),
            num_clips=num_clips,
            burn_captions=False
        )
    except MemoryError as mem_err:
        raise Exception("Out of memory during video processing. Please try with a shorter video or contact support for assistance with large files.") from mem_err
    except Exception as e:
        raise

     # Extract processed clips from result
    processed_clips_data = result.get('processed_clips', [])
    
    for clip_data in processed_clips_data:
        try:
            clip_path = Path(clip_data['clip_path'])
            caption_path = Path(clip_data.get('caption_path', '')) if clip_data.get('caption_path') else None
            
            # Upload clip file
            clip_s3_path = f"results/{filename}/{clip_path.name}"
            if not storage.save_file(str(clip_path), clip_s3_path):
                logger.error(f"Failed to upload clip to S3: {clip_s3_path}")
            
            # Upload caption file if exists
            if caption_path and caption_path.exists():
                caption_s3_path = f"results/{filename}/{caption_path.name}"
                if not storage.save_file(str(caption_path), caption_s3_path):
                    logger.error(f"Failed to upload caption to S3: {caption_s3_path}")
                    
        except Exception as clip_error:
            logger.error(f"Error processing clip {clip_data.get('clip_number', 'unknown')}: {clip_error}")
            continue
    
    # Cleanup temporary input file if downloaded from S3
    if temp_input_file and os.path.exists(temp_input_file.name):
        try:
            os.unlink(temp_input_file.name)
            logger.info(f"🧹 Cleaned up temporary file: {temp_input_file.name}")
        except Exception as cleanup_error:
            logger.warning(f"Failed to cleanup temporary file: {cleanup_error}")
    
    
    return result 

# Start the Serverless function when the script is run
if __name__ == '__main__':
    runpod.serverless.start({'handler': handler })