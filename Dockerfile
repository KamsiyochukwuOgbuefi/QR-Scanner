# Render Dockerfile for the QR Code Scanner Pro Flask app.
# A Dockerfile (instead of Render's native Python runtime) is used because
# the app depends on two native system libraries that pip cannot install:
#   - libzbar0  -> required by pyzbar (QR decoding)
#   - libgl1    -> required by opencv-python (image/camera processing)
#   - libglib2.0-0 -> runtime dependency of opencv-python on slim images

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Native system libraries needed by pyzbar + opencv-python.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libzbar0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for better build caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source.
COPY . .

# Run as a non-root user. The runtime history file lives in /app/data,
# which must stay writable for the current user.
RUN useradd --create-home --uid 1001 qruser \
    && mkdir -p /app/data \
    && chown -R qruser:qruser /app
USER qruser

# Render routes traffic to this port and sets PORT to match.
EXPOSE 10000

# Single worker: the app keeps in-memory state (camera session, scan
# history cache, live event queue), so more than one worker would break
# the shared singletons. Threads handle concurrent requests, and the long
# timeout keeps the MJPEG camera stream alive.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 8 --timeout 120 --keep-alive 5 app:app"]
