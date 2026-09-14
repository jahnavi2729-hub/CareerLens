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

# Copy application source code, helper scripts, and static frontend files
COPY src/ ./src/
COPY download_full.py ./
COPY careerlens.html market.html career-fit.html ./

# Copy data directory (contains gitkept folders or generated dataset)
COPY data/ ./data/

# Ensure dataset exists inside container: if jobs_clean.csv is missing, generate it during build
RUN python -c "\
import os, subprocess, sys; \
csv_path = os.path.join('data', 'processed', 'jobs_clean.csv'); \
if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0: \
    print('jobs_clean.csv missing. Generating dataset in Docker build...'); \
    subprocess.run([sys.executable, 'download_full.py'], check=True); \
    subprocess.run([sys.executable, '-m', 'src.preprocessing'], check=True); \
else: \
    print('Dataset data/processed/jobs_clean.csv verified.'); \
"

# Expose FastAPI server port
EXPOSE 8000

# Run uvicorn server binding to 0.0.0.0:8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
