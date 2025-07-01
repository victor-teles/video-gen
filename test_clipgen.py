#!/usr/bin/env python3
"""
Test script to isolate ClipGenerator initialization issues
"""
import tempfile
from pathlib import Path
import traceback

def test_clipgen():
    print("=== ClipGenerator Test ===")
    
    try:
        print("1. Testing imports...")
        from clip_generator import ClipGenerator
        print("✅ ClipGenerator imported successfully")
        
        print("2. Creating temporary output directory...")
        output_dir = Path(tempfile.mkdtemp())
        print(f"✅ Output directory created: {output_dir}")
        
        print("3. Creating ClipGenerator instance...")
        generator = ClipGenerator(str(output_dir))
        print(f"✅ ClipGenerator created: {generator}")
        print(f"✅ Generator type: {type(generator)}")
        
        print("4. Testing transcriber initialization...")
        print(f"   Before init - transcriber: {generator.transcriber}")
        generator._init_transcriber()
        print(f"✅ After init - transcriber: {generator.transcriber}")
        
        print("5. Testing clipfinder initialization...")
        print(f"   Before init - clipfinder: {generator.clipfinder}")
        generator._init_clipfinder()
        print(f"✅ After init - clipfinder: {generator.clipfinder}")
        
        print("\n🎉 All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        print(f"Error type: {type(e)}")
        print("Full traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_clipgen() 