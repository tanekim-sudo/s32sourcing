FROM python:3.12-slim

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /workspace/backend/requirements.txt
RUN pip install --no-cache-dir -r /workspace/backend/requirements.txt

COPY backend /workspace/backend
COPY rubric /workspace/rubric
COPY config /workspace/config

WORKDIR /workspace/backend
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace/backend

EXPOSE 8000

# Render/Railway set PORT; default 8000 for local Docker
ENV PORT=8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

CMD ["sh", "-c", "alembic upgrade head && python scripts/seed_demo.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
