# Use Python 3.10 slim image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (including ffmpeg for video processing)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    build-essential \
    libmagic1 \
    libmagic-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data required for ClipsAI
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"

RUN pip install nvidia-cudnn

# Copy application code
COPY . .

# Create storage directories
RUN mkdir -p storage/uploads storage/processing storage/results

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python3", "-u", "rp_handler.py"]