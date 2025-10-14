"""
Highlights extraction service for video processing
Adapted from backend2 for use with backend architecture
"""
import os
import re
import json
import requests
import logging

# Use backend's config module
import config

# Initialize logger
logger = logging.getLogger(__name__)

class HighlightsService:
    """Service for extracting highlight clips from video transcripts"""
    
    def __init__(self):
        """Initialize the highlights service"""
        # Get API key from backend config (uses OPENROUTER_API_KEY)
        self.api_key = config.OPENROUTER_API_KEY
        
        # Log whether we have an API key (without revealing the full key)
        if self.api_key:
            masked_key = f"{self.api_key[:4]}...{self.api_key[-4:]}" if len(self.api_key) > 8 else "***"
            logger.info(f"OpenRouter API key found (masked: {masked_key})")
        else:
            logger.warning("OpenRouter API key not found in configuration")
            logger.warning("Please set OPENROUTER_API_KEY environment variable")
        
        # Use backend's model configuration
        self.models = config.CLIP_SELECTION_ALL_MODELS
    
    async def get_highlights(self, transcript, num_clips=2):
        """
        Get highlight clips using OpenRouter API with multiple model fallbacks.
        
        Args:
            transcript: The transcript text with timestamps
            num_clips: Number of highlight clips to extract (default: 2)
            
        Returns:
            List of dictionaries with start and end times
        """
        # Validate API key format
        if not self.api_key or not self.api_key.startswith("sk-"):
            logger.warning("API key missing or invalid format")
            return await self._get_fallback_highlights(num_clips)
        
        logger.info(f"Getting {num_clips} highlights from transcript using OpenRouter API")
        
        # Define system prompt for better highlight extraction
        system_prompt = f"""
        You are an expert video editor who specializes in finding the most engaging segments in videos.
        Based on the transcript with timestamps, identify exactly {num_clips} separate highlights that would make compelling short-form videos.
        
        For each highlight:
        1. Choose emotionally impactful, insightful, or entertaining segments
        2. Select continuous portions between 10-120 seconds each depending on the content
        3. Ensure each highlight is self-contained and makes sense on its own
        4. Include precise start and end timestamps
        5. Provide a brief reason why this segment is engaging
        6. Create a short, catchy title (2-5 words) that captures the essence of the segment
        
        Only return your response as a valid JSON array with this exact format:
        [
            {{
                "start_time": <start_time_in_seconds>,
                "end_time": <end_time_in_seconds>,
                "reason": "<reason_this_is_a_good_highlight>",
                "title": "<short_2_to_5_word_title>"
            }},
            ...
        ]
        
        Ensure EXACTLY {num_clips} highlights are provided. If there aren't enough clear highlights, 
        make your best selection based on available content.
        """
        
        # Headers for OpenRouter API
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Try each model in sequence until one works
        last_error = None
        for model_index, model in enumerate(self.models):
            logger.info(f"Trying model ({model_index+1}/{len(self.models)}): {model}")
            
            # Data for OpenRouter API
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript}
                ],
                "temperature": config.CLIP_SELECTION_TEMPERATURE,
                "max_tokens": config.CLIP_SELECTION_MAX_TOKENS
            }
            
            try:
                # Make API request
                logger.info(f"Sending request to OpenRouter with model: {model}")
                
                response = requests.post(
                    f"{config.OPENROUTER_BASE_URL}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=60  # Add timeout to prevent hanging
                )
                
                # Check response
                if response.status_code != 200:
                    logger.warning(f"Error from OpenRouter API with model {model}: {response.status_code}")
                    logger.warning(f"Response: {response.text}")
                    last_error = f"HTTP {response.status_code}: {response.text}"
                    continue  # Try next model
                
                # Parse response
                response_data = response.json()
                
                # Print token usage for cost monitoring
                if "usage" in response_data:
                    logger.info(f"Token usage: {response_data['usage']['total_tokens']} tokens")
                
                # Extract content
                try:
                    assistant_message = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    # Try to extract JSON from the content
                    json_match = re.search(r'\[.*\]', assistant_message, re.DOTALL)
                    if json_match:
                        assistant_message = json_match.group(0)
                    
                    # Parse JSON
                    highlights = json.loads(assistant_message)
                    
                    # Validate highlights
                    valid_highlights = []
                    for highlight in highlights:
                        if "start_time" in highlight and "end_time" in highlight:
                            # Ensure timestamps are numbers
                            start = float(highlight["start_time"])
                            end = float(highlight["end_time"])
                            
                            # Validate durations (use backend config)
                            duration = end - start
                            if config.MIN_CLIP_DURATION <= duration <= config.MAX_CLIP_DURATION:
                                valid_highlights.append({
                                    "start_time": start,
                                    "end_time": end,
                                    "reason": highlight.get("reason", "Interesting segment"),
                                    "title": highlight.get("title", "Untitled")
                                })
                    
                    if len(valid_highlights) < num_clips:
                        logger.warning(f"Only found {len(valid_highlights)} valid highlights out of {num_clips} requested")
                        # Try next model if we don't have enough highlights
                        last_error = f"Only found {len(valid_highlights)} valid highlights"
                        continue
                    
                    logger.info(f"Successfully extracted {len(valid_highlights)} highlights using model: {model}")
                    return valid_highlights[:num_clips]  # Return exactly num_clips
                    
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Error parsing OpenRouter response with model {model}: {e}")
                    last_error = f"JSON parse error: {e}"
                    continue  # Try next model
                    
            except Exception as e:
                logger.warning(f"Error calling OpenRouter API with model {model}: {e}")
                last_error = str(e)
                continue  # Try next model
        
        # If all models failed, use fallback highlights
        logger.warning(f"All OpenRouter models failed: {last_error}")
        logger.warning("Using fallback highlights instead")
        return await self._get_fallback_highlights(num_clips)
    
    async def _get_fallback_highlights(self, num_clips=2):
        """
        Fallback highlights to use if all OpenRouter API attempts fail.
        Generates more meaningful highlights instead of automatic segmentation.
        """
        # Base duration for each highlight (use backend config)
        highlight_duration = max(config.MIN_CLIP_DURATION, 20)  # At least 20 seconds
        
        # Predefined interesting reasons for fallback highlights
        reasons = [
            "Key discussion point in the video",
            "Important information segment", 
            "Engaging conversation moment",
            "Notable explanation section",
            "Compelling visual sequence"
        ]
        
        # Predefined short titles (2-5 words)
        titles = [
            "Key Point",
            "Important Info", 
            "Engaging Moment",
            "Notable Explanation",
            "Visual Highlight"
        ]
        
        # Generate highlights with meaningful reasons
        all_highlights = []
        for i in range(num_clips):
            start_time = 20 + (i * 30)  # Start at 20s, then space out by 30s
            reason_index = i % len(reasons)
            all_highlights.append({
                'start_time': start_time,
                'end_time': start_time + highlight_duration,
                'reason': reasons[reason_index], 
                'title': titles[reason_index]
            })
        
        logger.info(f"Generated {len(all_highlights)} fallback highlights with meaningful reasons and titles")
        return all_highlights