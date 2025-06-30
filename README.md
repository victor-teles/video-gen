# 🎬 Video Clip Generator with AI-Powered Cropping

An intelligent CLI tool that automatically generates video clips from long-form content with word-level captions and smart cropping for social media.

## ✨ Features

- **🤖 Intelligent Clip Detection**: Uses [ClipsAI](https://www.clipsai.com/) to automatically find the best moments
- **🎯 Smart Auto-Cropping**: YOLO-powered object detection for optimal crop positioning
- **📝 Word-Level Captions**: WhisperX-generated JSON captions with precise timing
- **📐 Multiple Aspect Ratios**: Support for 9:16, 1:1, 16:9, and custom ratios
- **🎥 High-Quality Output**: Professional-grade H.264 encoding with optimized settings
- **⚡ CLI Interface**: Simple command-line usage for batch processing

## 🛠️ Dependencies

### Python Libraries
- **ClipsAI**: Intelligent clip detection from long-form videos
- **WhisperX**: Enhanced Whisper with word-level timestamps
- **YOLOv8**: Object detection for smart cropping
- **OpenCV**: Video processing
- **PyTorch**: Deep learning backend

### System Requirements
- **FFmpeg**: Video encoding/decoding (must be installed system-wide)
- **Python 3.8+**: Required for all dependencies

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Run the automated setup
python setup.py

# Or manual setup:
python -m venv clip_generator_env

# Windows
clip_generator_env\Scripts\activate

# Linux/Mac
source clip_generator_env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Install FFmpeg
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
- **macOS**: `brew install ffmpeg`
- **Ubuntu/Debian**: `sudo apt install ffmpeg`

### 3. Generate Clips
```bash
python clip_generator.py \
  --input your_video.mp4 \
  --num-clips 5 \
  --ratio 9:16 \
  --output-dir ./output
```

## 📖 Usage

### Basic Usage
```bash
python clip_generator.py --input VIDEO --num-clips NUM --ratio RATIO [--output-dir DIR]
```

### Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--input` | ✅ | Path to input video file | `video.mp4` |
| `--num-clips` | ✅ | Number of clips to generate | `5` |
| `--ratio` | ✅ | Target aspect ratio | `9:16`, `1:1`, `16:9` |
| `--output-dir` | ❌ | Output directory | `./clips` (default: `./output`) |

### Examples

#### Generate TikTok/Instagram Reels (9:16)
```bash
python clip_generator.py --input podcast.mp4 --num-clips 3 --ratio 9:16 --output-dir ./vertical_clips
```

#### Generate Instagram Square Posts (1:1)
```bash
python clip_generator.py --input interview.mp4 --num-clips 5 --ratio 1:1 --output-dir ./square_clips
```

#### Generate YouTube Shorts (9:16)
```bash
python clip_generator.py --input webinar.mp4 --num-clips 10 --ratio 9:16 --output-dir ./youtube_shorts
```

## 📁 Output Structure

For each generated clip, you'll get:

```
output/
├── clip_01_turning_passive_vocabulary.mp4    # Video clip
├── clip_01_turning_passive_vocabulary.json   # Word-level captions
├── clip_02_effective_learning_strategies.mp4
├── clip_02_effective_learning_strategies.json
└── ...
```

### Caption JSON Format
```json
{
  "text": "Turning passive vocabulary into active.",
  "segments": [
    {
      "id": 0,
      "start": 0.003999999999990678,
      "end": 3.2700000000000102,
      "text": "Turning passive vocabulary into active.",
      "words": [
        {
          "word": "Turning",
          "start": 0.003999999999990678,
          "end": 0.32399999999998386
        },
        {
          "word": "passive",
          "start": 0.42499999999998295,
          "end": 0.8650000000000091
        }
      ]
    }
  ]
}
```

## 🔧 How It Works

### 1. **Video Analysis**
- Uses WhisperX to transcribe audio with word-level timestamps
- ClipsAI analyzes transcript to identify engaging segments

### 2. **Clip Selection**
- Ranks clips by duration and content quality
- Selects top N clips based on your specification
- Filters clips between 3-120 seconds

### 3. **Intelligent Cropping**
- **YOLO Detection**: Identifies people, objects, and points of interest
- **Smart Positioning**: Calculates optimal crop position based on detected objects
- **Smooth Transitions**: Gradually adjusts crop position for stable video
- **Fallback**: Uses center crop if no objects detected

### 4. **High-Quality Encoding**
- **Video**: H.264 with CRF 18 (visually lossless quality)
- **Audio**: AAC at 192k bitrate
- **Optimization**: Removes metadata, optimizes for social media

## ⚙️ Advanced Configuration

### Customizing YOLO Detection
Edit these parameters in `ClipGenerator.__init__()`:
```python
self.yolo_model = YOLO("yolov8n.pt")  # Model size: n, s, m, l, x
```

### Adjusting Crop Sensitivity
Modify in `auto_crop_with_yolo()`:
```python
update_interval = 30      # Frames between detection updates
conf=0.3                  # Detection confidence threshold
class_weight = 2.0        # Weight for person detection
```

### Quality Settings
Modify in `extract_high_quality_clip()`:
```python
'-crf', '18'              # Quality (lower = higher quality)
'-preset', 'slow'         # Encoding speed vs quality
'-b:a', '192k'           # Audio bitrate
```

## 🐛 Troubleshooting

### Common Issues

#### FFmpeg Not Found
```bash
❌ Error: ffmpeg not found. Please install ffmpeg first.
```
**Solution**: Install FFmpeg system-wide from [ffmpeg.org](https://ffmpeg.org/download.html)

#### ClipsAI Import Error
```bash
❌ Error importing ClipsAI
```
**Solution**: 
```bash
pip install clipsai
```

#### WhisperX Import Error
```bash
❌ Error importing WhisperX
```
**Solution**:
```bash
pip install git+https://github.com/m-bain/whisperx.git
```

#### YOLO Not Available
```bash
⚠️ Warning: YOLO not available
```
**Solution**: 
```bash
pip install ultralytics
```
Note: Tool will fall back to center crop if YOLO unavailable.

#### OpenCV Video Writer Failed
```bash
⚠️ OpenCV writer failed, falling back to FFmpeg...
```
**Solution**: This is normal - the tool automatically uses FFmpeg as fallback.

### Performance Tips

1. **Use GPU**: Install CUDA-compatible PyTorch for faster YOLO inference
2. **Model Size**: Use `yolov8n.pt` for speed, `yolov8x.pt` for accuracy
3. **Batch Processing**: Process multiple videos sequentially for efficiency

## 📊 Performance Expectations

| Video Length | Processing Time | Output Quality |
|--------------|----------------|----------------|
| 5 minutes | ~2-3 minutes | High |
| 30 minutes | ~10-15 minutes | High |
| 1 hour | ~20-30 minutes | High |
| 2+ hours | ~45+ minutes | High |

*Times vary based on hardware, video resolution, and number of clips*

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add your improvements
4. Submit a pull request

## 📄 License

This project is open source. Please check individual dependencies for their licensing terms.

## 🔗 Related Projects

- [ClipsAI](https://www.clipsai.com/) - Intelligent video clipping
- [WhisperX](https://github.com/m-bain/whisperx) - Enhanced Whisper transcription
- [YOLOv8](https://github.com/ultralytics/ultralytics) - Object detection

---

**Ready to create amazing clips? Get started now! 🚀** 