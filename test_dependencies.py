#!/usr/bin/env python3
"""
Dependency Test Script for Video Clip Generator
===============================================

This script tests all dependencies to ensure they're properly installed.
"""

import sys
import subprocess
import importlib

def test_import(module_name, package_name=None, description=""):
    """Test if a module can be imported"""
    try:
        importlib.import_module(module_name)
        print(f"✅ {description or module_name}")
        return True
    except ImportError as e:
        print(f"❌ {description or module_name}: {e}")
        if package_name:
            print(f"   Install with: pip install {package_name}")
        return False

def test_system_command(cmd, description):
    """Test if a system command is available"""
    try:
        result = subprocess.run(cmd, capture_output=True, check=True, timeout=10)
        print(f"✅ {description}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        print(f"❌ {description}")
        return False

def main():
    print("🧪 Testing Video Clip Generator Dependencies")
    print("=" * 50)
    
    all_good = True
    
    # Test Python version
    print(f"🐍 Python Version: {sys.version}")
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        all_good = False
    else:
        print("✅ Python version OK")
    
    print("\n📦 Testing Python Dependencies:")
    print("-" * 30)
    
    # Core dependencies
    tests = [
        ("clipsai", "clipsai", "ClipsAI"),
        ("whisperx", "git+https://github.com/m-bain/whisperx.git", "WhisperX"),
        ("ultralytics", "ultralytics", "YOLOv8"),
        ("cv2", "opencv-python", "OpenCV"),
        ("torch", "torch", "PyTorch"),
        ("numpy", "numpy", "NumPy"),
        ("pathlib", None, "Pathlib (built-in)"),
        ("json", None, "JSON (built-in)"),
        ("argparse", None, "Argparse (built-in)"),
        ("subprocess", None, "Subprocess (built-in)"),
        ("os", None, "OS (built-in)"),
        ("sys", None, "Sys (built-in)"),
        ("tempfile", None, "Tempfile (built-in)"),
        ("shutil", None, "Shutil (built-in)"),
        ("re", None, "Regular Expressions (built-in)")
    ]
    
    for module, package, description in tests:
        success = test_import(module, package, description)
        if not success:
            all_good = False
    
    print("\n🔧 Testing System Dependencies:")
    print("-" * 30)
    
    # Test FFmpeg
    ffmpeg_success = test_system_command(['ffmpeg', '-version'], "FFmpeg")
    if not ffmpeg_success:
        print("   Install from: https://ffmpeg.org/download.html")
        all_good = False
    
    print("\n🎯 Testing Core Functionality:")
    print("-" * 30)
    
    # Test ClipsAI components
    try:
        from clipsai import ClipFinder, Transcriber
        print("✅ ClipsAI components importable")
    except ImportError as e:
        print(f"❌ ClipsAI components: {e}")
        all_good = False
    
    # Test YOLO model loading (optional)
    try:
        from ultralytics import YOLO
        print("✅ YOLO available for smart cropping")
        try:
            # Try loading a small model (this will download if not present)
            print("🔄 Testing YOLO model loading...")
            model = YOLO("yolov8n.pt")
            print("✅ YOLO model loaded successfully")
        except Exception as e:
            print(f"⚠️  YOLO model loading failed: {e}")
            print("   This is OK - will use center crop fallback")
    except ImportError:
        print("⚠️  YOLO not available - will use center crop fallback")
    
    # Test OpenCV video capabilities
    try:
        import cv2
        print("✅ OpenCV video capabilities available")
    except ImportError:
        print("❌ OpenCV not available")
        all_good = False
    
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 All dependencies are properly installed!")
        print("\n📋 Ready to generate clips:")
        print("python clip_generator.py --input video.mp4 --num-clips 5 --ratio 9:16")
    else:
        print("❌ Some dependencies are missing or broken.")
        print("\n🔧 To fix issues:")
        print("1. Run: python setup.py")
        print("2. Install missing system dependencies")
        print("3. Rerun this test")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main()) 