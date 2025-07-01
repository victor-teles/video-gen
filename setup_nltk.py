#!/usr/bin/env python3
"""
Setup script to download required NLTK data
"""
import nltk
import os

def download_nltk_data():
    """Download required NLTK data packages"""
    print("🔄 Downloading NLTK data packages...")
    
    # Create NLTK data directory if it doesn't exist
    nltk_data_dir = os.path.expanduser('~/nltk_data')
    os.makedirs(nltk_data_dir, exist_ok=True)
    
    # Download required packages
    packages = ['punkt', 'punkt_tab']
    
    for package in packages:
        try:
            print(f"📥 Downloading {package}...")
            nltk.download(package, quiet=False)
            print(f"✅ {package} downloaded successfully")
        except Exception as e:
            print(f"❌ Failed to download {package}: {e}")
    
    print("✅ NLTK data setup completed!")

if __name__ == "__main__":
    download_nltk_data() 