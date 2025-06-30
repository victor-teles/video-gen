@echo off
setlocal enabledelayedexpansion

echo 🐳 Video Clip Generator - Docker Build ^& Test Script
echo ====================================================

:: Check if Docker is running
echo 📋 Checking Docker...
docker info >nul 2>&1
if !errorlevel! neq 0 (
    echo ❌ Docker is not running. Please start Docker Desktop and try again.
    exit /b 1
)
echo ✅ Docker is running

:: Build images
echo.
echo 🔨 Building Docker images...
echo This may take 5-10 minutes for the first build...

:: Build main app
echo 📦 Building main application...
docker-compose build web
if !errorlevel! neq 0 (
    echo ❌ Failed to build main application
    exit /b 1
)

:: Build worker
echo 📦 Building Celery worker...
docker-compose build worker
if !errorlevel! neq 0 (
    echo ❌ Failed to build worker
    exit /b 1
)

echo ✅ Images built successfully

:: Start services
echo.
echo 🚀 Starting services...
docker-compose up -d
if !errorlevel! neq 0 (
    echo ❌ Failed to start services
    exit /b 1
)

:: Wait for services to be ready
echo ⏳ Waiting for services to start...
timeout /t 30 /nobreak >nul

:: Check if services are running
echo.
echo 🔍 Checking service status...

:: Check Redis
docker-compose exec redis redis-cli ping | findstr "PONG" >nul
if !errorlevel! equ 0 (
    echo ✅ Redis: Running
) else (
    echo ❌ Redis: Not responding
    docker-compose down
    exit /b 1
)

:: Check main app
curl -f http://localhost:8000/api/health >nul 2>&1
if !errorlevel! equ 0 (
    echo ✅ FastAPI: Running
) else (
    echo ❌ FastAPI: Not responding
    echo 📋 Checking logs...
    docker-compose logs web
    docker-compose down
    exit /b 1
)

echo.
echo 🧪 Running automated tests...
python test-docker.py
if !errorlevel! neq 0 (
    echo ❌ Tests failed
    docker-compose down
    exit /b 1
)

echo.
echo 🎉 All tests passed!
echo.
echo 📊 Your services are running at:
echo    🌐 Main API: http://localhost:8000
echo    📖 API Docs: http://localhost:8000/docs
echo    🔍 Redis: localhost:6379
echo.
echo 📋 Available commands:
echo    docker-compose logs web     # View API logs
echo    docker-compose logs worker  # View worker logs
echo    docker-compose down         # Stop all services
echo.
echo 🧪 To test with S3 instead of local storage:
echo    1. Set your AWS credentials in environment
echo    2. Run: docker-compose -f docker-compose.s3.yml up

pause 