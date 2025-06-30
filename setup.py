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
    print("🚀 Video Clip Generator Setup")
    print("=" * 50)
    
    # Check if Python is available
    try:
        python_version = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
        print(f"✅ Python found: {python_version.stdout.strip()}")
    except Exception as e:
        print(f"❌ Python not found: {e}")
        sys.exit(1)
    
    # Create virtual environment
    venv_name = "clip_generator_env"
    if not os.path.exists(venv_name):
        if not run_command(f"python -m venv {venv_name}", "Creating virtual environment"):
            sys.exit(1)
    else:
        print(f"✅ Virtual environment '{venv_name}' already exists")
    
    # Determine activation command based on OS
    if os.name == 'nt':  # Windows
        activate_cmd = f"{venv_name}\\Scripts\\activate"
        pip_cmd = f"{venv_name}\\Scripts\\pip"
    else:  # Unix/Linux/Mac
        activate_cmd = f"source {venv_name}/bin/activate"
        pip_cmd = f"{venv_name}/bin/pip"
    
    # Upgrade pip
    if not run_command(f"{pip_cmd} install --upgrade pip", "Upgrading pip"):
        sys.exit(1)
    
    # Install requirements
    if not run_command(f"{pip_cmd} install -r requirements.txt", "Installing Python dependencies"):
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✅ Setup completed successfully!")
    print("\n📋 Next steps:")
    print(f"1. Activate the virtual environment:")
    if os.name == 'nt':
        print(f"   {venv_name}\\Scripts\\activate")
    else:
        print(f"   source {venv_name}/bin/activate")
    
    print("\n2. Install system dependencies:")
    print("   - FFmpeg: https://ffmpeg.org/download.html")
    
    print("\n3. Run the clip generator:")
    print("   python clip_generator.py --input video.mp4 --num-clips 5 --ratio 9:16 --output-dir ./output")
    
    print("\n📖 For more information, see README.md")

if __name__ == "__main__":
    main() 