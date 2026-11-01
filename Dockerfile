# Official lightweight Python runtime
FROM python:3.11-slim

# Python environment settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies: Stockfish UCI engine and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    stockfish \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Configure Stockfish path for Debian/Ubuntu
ENV STOCKFISH_PATH=/usr/games/stockfish

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app/

# Ensure runtime directories exist
RUN mkdir -p /app/uploads

# Expose application port
EXPOSE 5000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT:-5000}/api/health || exit 1

# Launch production WSGI server with Gunicorn
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-5000} --workers 2 --threads 4 --timeout 120"]
