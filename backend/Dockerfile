# ============================================================
# UAH Backend — Dockerfile (DEV)
# ============================================================
# Multi-stage not needed for dev; single stage keeps it simple.
# Uvicorn runs with --reload so code changes are picked up
# automatically when you bind-mount the app/ directory.
# ============================================================

FROM python:3.12-slim

# Prevents Python from writing .pyc files and buffers stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8000

# Start Uvicorn with hot-reload for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

