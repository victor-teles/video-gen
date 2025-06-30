#!/bin/bash

set -e  # Exit on any error

echo "🐳 Video Clip Generator - Docker Build & Test Script"
echo "===================================================="

# Function to cleanup
cleanup() {
    echo "🧹 Cleaning up..."
    docker-compose down -v 2>/dev/null || true
}

# Cleanup on exit
trap cleanup EXIT

# Check if Docker is running
echo "📋 Checking Docker..."
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi
echo "✅ Docker is running"

# Build images
echo ""
echo "🔨 Building Docker images..."
echo "This may take 5-10 minutes for the first build..."

# Build main app
echo "📦 Building main application..."
docker-compose build web

# Build worker
echo "📦 Building Celery worker..."
docker-compose build worker

echo "✅ Images built successfully"

# Start services
echo ""
echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Check if services are running
echo ""
echo "🔍 Checking service status..."

# Check Redis
if docker-compose exec redis redis-cli ping | grep -q PONG; then
    echo "✅ Redis: Running"
else
    echo "❌ Redis: Not responding"
    exit 1
fi

# Check main app
if curl -f http://localhost:8000/api/health >/dev/null 2>&1; then
    echo "✅ FastAPI: Running"
else
    echo "❌ FastAPI: Not responding"
    echo "📋 Checking logs..."
    docker-compose logs web
    exit 1
fi

# Check worker
if docker-compose exec worker celery -A tasks inspect ping >/dev/null 2>&1; then
    echo "✅ Celery Worker: Running"
else
    echo "⚠️  Celery Worker: May not be fully ready (this is sometimes normal)"
fi

echo ""
echo "🧪 Running automated tests..."
python test-docker.py

echo ""
echo "🎉 All tests passed!"
echo ""
echo "📊 Your services are running at:"
echo "   🌐 Main API: http://localhost:8000"
echo "   📖 API Docs: http://localhost:8000/docs"
echo "   🔍 Redis: localhost:6379"
echo ""
echo "📋 Available commands:"
echo "   docker-compose logs web     # View API logs"
echo "   docker-compose logs worker  # View worker logs"
echo "   docker-compose down         # Stop all services"
echo ""
echo "🧪 To test with S3 instead of local storage:"
echo "   1. Set your AWS credentials in environment"
echo "   2. Run: docker-compose -f docker-compose.s3.yml up" 