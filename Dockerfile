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
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code, datasets, and static frontend files
COPY src/ ./src/
COPY data/ ./data/
COPY careerlens.html market.html career-fit.html ./

# Expose FastAPI server port
EXPOSE 8000

# Run uvicorn server binding to 0.0.0.0:8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
