#!/usr/bin/env python3
"""
Setup script for Video Clip Generator
=====================================

This script sets up a virtual environment and installs all required dependencies.
"""

import subprocess
import sys
import os
from pathlib import Path
from setuptools import setup, find_packages

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description.lower()}: {e}")
        print(f"Command output: {e.stdout}")
        print(f"Command error: {e.stderr}")
        return False

def main():
    setup(
        name="video_clip_generator",
        version="2.0.4",
        description="Video Clip Generator with AI-powered features",
        author="SmartClipAI",
        packages=find_packages(),
        install_requires=[
            "celery",
            "redis",
            "sqlalchemy",
            "psycopg2-binary",
            "fastapi",
            "uvicorn",
            "python-multipart",
            "moviepy",
            "openai",
            "replicate",
            "clipsai",
            "whisperx",
            "ultralytics",
            "opencv-python",
            "torch",
            "numpy",
            "Pillow"
        ],
        python_requires=">=3.8",
    )

if __name__ == "__main__":
    main() 