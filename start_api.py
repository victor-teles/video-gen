"""
Startup script for the Video Clip Generator API
"""
import subprocess
import sys
import time
import os
import signal
from pathlib import Path

def check_redis():
    """Check if Redis is running"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=2)
        r.ping()
        print("✅ Redis is running")
        return True
    except ImportError:
        print("❌ Redis Python module not installed")
        return False
    except Exception as e:
        print(f"❌ Redis is not running: {e}")
        return False

def check_s3_connection():
    """Check S3 connectivity and bucket setup"""
    try:
        import boto3
        from botocore.exceptions import ClientError
        import config
        
        if config.STORAGE_TYPE != 's3':
            print("ℹ️  Using local storage (S3 not configured)")
            return True
            
        print("🔄 Checking S3 configuration...")
        
        # Check if AWS credentials are set
        if not all([config.AWS_ACCESS_KEY_ID, config.AWS_SECRET_ACCESS_KEY, config.AWS_REGION]):
            print("❌ AWS credentials not configured in .env file")
            return False
            
        # Initialize S3 client
        s3 = boto3.client('s3',
            endpoint_url=config.S3_ENDPOINT_URL,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            region_name=config.AWS_REGION
        )
        
        # Check if bucket exists and is accessible
        try:
            s3.head_bucket(Bucket=config.S3_BUCKET_NAME)
            print(f"✅ Connected to S3 bucket: {config.S3_BUCKET_NAME}")
            
            # Check required folders
            required_folders = ['uploads/', 'processing/', 'results/']
            existing_folders = set()
            
            response = s3.list_objects_v2(
                Bucket=config.S3_BUCKET_NAME,
                Delimiter='/'
            )
            
            if 'CommonPrefixes' in response:
                existing_folders = {p['Prefix'] for p in response['CommonPrefixes']}
            
            missing_folders = [f for f in required_folders if f not in existing_folders]
            
            if missing_folders:
                print("⚠️  Creating missing S3 folders:")
                for folder in missing_folders:
                    s3.put_object(Bucket=config.S3_BUCKET_NAME, Key=folder)
                    print(f"   ✅ Created: {folder}")
            
            # Verify bucket configuration
            try:
                versioning = s3.get_bucket_versioning(Bucket=config.S3_BUCKET_NAME)
                if versioning.get('Status') == 'Enabled':
                    print("✅ Bucket versioning: Enabled")
                else:
                    print("⚠️  Bucket versioning: Not enabled")
                
                lifecycle = s3.get_bucket_lifecycle_configuration(Bucket=config.S3_BUCKET_NAME)
                if lifecycle.get('Rules'):
                    print("✅ Lifecycle policies: Configured")
                    
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchLifecycleConfiguration':
                    print("⚠️  Lifecycle policies: Not configured")
                else:
                    raise e
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                print(f"❌ S3 bucket '{config.S3_BUCKET_NAME}' does not exist")
            elif error_code == 'AccessDenied':
                print(f"❌ Access denied to S3 bucket '{config.S3_BUCKET_NAME}'")
            else:
                print(f"❌ S3 error: {str(e)}")
            return False
            
    except ImportError:
        print("❌ AWS SDK (boto3) not installed")
        return False
    except Exception as e:
        print(f"❌ S3 configuration error: {str(e)}")
        return False

def start_redis():
    """Start Redis server"""
    print("🚀 Starting Redis server...")
    try:
        # Try to start Redis using common commands
        redis_commands = ["redis-server", "redis-server.exe"]
        
        for cmd in redis_commands:
            try:
                subprocess.Popen([cmd], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
                time.sleep(2)  # Wait for Redis to start
                if check_redis():
                    return True
            except FileNotFoundError:
                continue
        
        print("❌ Could not start Redis automatically")
        print("   Please install and start Redis manually:")
        print("   - Windows: Download from https://redis.io/download")
        print("   - Linux/Mac: sudo apt-get install redis-server / brew install redis")
        return False
        
    except Exception as e:
        print(f"❌ Error starting Redis: {e}")
        return False

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def start_celery():
    """Start Celery worker"""
    print("🔧 Starting Celery worker...")
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path.cwd())
        
        celery_cmd = [
            sys.executable, "-m", "celery", 
            "-A", "tasks.celery_app",
            "worker", 
            "--loglevel=info",
            "--pool=solo"  # For Windows compatibility
        ]
        
        celery_process = subprocess.Popen(celery_cmd, env=env)
        print("✅ Celery worker started")
        return celery_process
        
    except Exception as e:
        print(f"❌ Failed to start Celery worker: {e}")
        return None

def start_fastapi(config):
    """Start FastAPI server"""
    print("🌐 Starting FastAPI server...")
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path.cwd())
        
        uvicorn_cmd = [
            sys.executable, "-m", "uvicorn",
            "main:app",
            "--host", config.API_HOST,
            "--port", str(config.API_PORT),
            "--reload"  # 🔄 Auto-reload on file changes
        ]
        
        # Add reload flag if in development mode
        if config.AUTO_RELOAD:
            uvicorn_cmd.append("--reload")
        
        fastapi_process = subprocess.Popen(uvicorn_cmd, env=env)
        print(f"✅ FastAPI server started at http://localhost:{config.API_PORT}")
        print(f"📚 API documentation: http://localhost:{config.API_PORT}/docs")
        return fastapi_process
        
    except Exception as e:
        print(f"❌ Failed to start FastAPI server: {e}")
        return None

def main():
    """Main startup function"""
    print("🎬 Video Clip Generator API - Startup Script")
    print("=" * 50)
    
    # Import config for use throughout the function
    try:
        import config
    except ImportError:
        print("❌ Could not import config. Using defaults.")
        config = type('Config', (), {
            'API_HOST': '0.0.0.0',
            'API_PORT': 8000,
            'AUTO_RELOAD': True
        })()
    
    # Track processes for cleanup
    processes = []
    
    try:
        # Step 1: Install dependencies
        if not install_dependencies():
            return
        
        # Step 2: Check S3 configuration
        if not check_s3_connection():
            print("\n⚠️  S3 storage is not properly configured")
            print("   Please run 's3_setup.bat' to configure S3 storage")
            print("   Or set STORAGE_TYPE=local in .env to use local storage")
            return
        
        # Step 3: Check/Start Redis
        if not check_redis():
            if not start_redis():
                print("\n❌ Cannot proceed without Redis. Please start Redis manually and try again.")
                return
        
        # Wait a moment for Redis to be fully ready
        time.sleep(1)
        
        # Step 4: Start Celery worker
        celery_process = start_celery()
        if celery_process:
            processes.append(celery_process)
        else:
            print("❌ Cannot proceed without Celery worker")
            return
        
        # Wait for Celery to initialize
        time.sleep(3)
        
        # Step 5: Start FastAPI server
        fastapi_process = start_fastapi(config)
        if fastapi_process:
            processes.append(fastapi_process)
        else:
            print("❌ Cannot proceed without FastAPI server")
            return
        
        print("\n🎉 All services started successfully!")
        print("=" * 50)
        print("📋 Service Status:")
        print("   ✅ Redis Server: Running")
        print("   ✅ Celery Worker: Running")
        print(f"   ✅ FastAPI Server: http://localhost:{config.API_PORT}")
        if config.STORAGE_TYPE == 's3':
            print(f"   ✅ S3 Storage: Connected to {config.S3_BUCKET_NAME}")
        else:
            print("   ✅ Local Storage: Enabled")
        print(f"   📚 API Docs: http://localhost:{config.API_PORT}/docs")
        print("\n⚠️  Press Ctrl+C to stop all services")
        
        # Keep the script running and wait for shutdown signal
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutdown signal received...")
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        
    finally:
        # Cleanup: Stop all processes
        print("🧹 Stopping all services...")
        for process in processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ Process {process.pid} stopped")
            except:
                try:
                    process.kill()
                    print(f"⚠️  Force killed process {process.pid}")
                except:
                    pass
        
        print("✅ All services stopped. Goodbye!")

if __name__ == "__main__":
    main() 