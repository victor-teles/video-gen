FROM nvidia/cuda:13.0.0-cudnn-runtime-ubuntu24.04

WORKDIR /app

RUN apt update && apt install software-properties-common -y
RUN add-apt-repository ppa:deadsnakes/ppa && apt update

RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3.10-dev \
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


RUN ls -la /usr/bin/python3 && rm /usr/bin/python3 && ln -s python3.10 /usr/bin/python3

RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data required for ClipsAI
RUN python3 -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"

# Copy application code
COPY . .

# Create storage directories
RUN mkdir -p storage/uploads storage/processing storage/results

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python3", "-u", "rp_handler.py"]