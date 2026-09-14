# Use official slim Python base image
FROM python:3.11-slim

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Set working directory inside container
WORKDIR /app

# Copy requirement files first for optimal Docker layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir uvicorn fastapi pypdf python-docx python-multipart python-dotenv openai && \
    python -c "import uvicorn; print('uvicorn installation verified:', uvicorn.__file__)"

# Copy application source code, helper scripts, and static frontend files
COPY src/ ./src/
COPY download_full.py ./
COPY careerlens.html market.html career-fit.html ./

# Create data directories and generate dataset inside the image during Docker build
RUN mkdir -p data/raw data/processed && \
    python download_full.py && \
    python -m src.preprocessing

# Expose FastAPI server port
EXPOSE 8000

# Run uvicorn server binding to 0.0.0.0:8000
CMD sh -c "PYTHONPATH=. python -m uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"
