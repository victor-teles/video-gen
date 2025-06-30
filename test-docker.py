#!/usr/bin/env python3
"""
Test script to verify Docker setup works
"""
import requests
import time
import sys

def test_api_health():
    """Test if the API is responding"""
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ API Health Check: PASSED")
            return True
        else:
            print(f"❌ API Health Check: FAILED (Status: {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ API Health Check: FAILED (Error: {e})")
        return False

def test_storage_connection():
    """Test storage connection"""
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            storage_status = data.get("storage", "Unknown")
            print(f"✅ Storage Status: {storage_status}")
            return True
        else:
            print(f"❌ Storage Test: FAILED (Status: {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Storage Test: FAILED (Error: {e})")
        return False

def test_upload_endpoint():
    """Test if upload endpoint is accessible"""
    try:
        # We just test if the endpoint exists (it should return 422 for missing file)
        response = requests.post("http://localhost:8000/api/upload-video", timeout=5)
        if response.status_code == 422:  # Expected: missing file parameter
            print("✅ Upload Endpoint: ACCESSIBLE")
            return True
        else:
            print(f"❌ Upload Endpoint: Unexpected response (Status: {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Upload Endpoint: FAILED (Error: {e})")
        return False

def main():
    print("🐳 Testing Docker Setup...")
    print("=" * 50)
    
    # Wait for services to start
    print("⏳ Waiting for services to start...")
    time.sleep(10)
    
    tests = [
        test_api_health,
        test_storage_connection,
        test_upload_endpoint
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        time.sleep(1)
    
    print("=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Docker setup is working correctly.")
        sys.exit(0)
    else:
        print("⚠️ Some tests failed. Check the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 