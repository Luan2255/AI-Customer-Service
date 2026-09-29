# Start from a small supported Python runtime.
FROM python:3.12-slim

# Avoid bytecode files and enable immediate container log output.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install dependencies separately so Docker can cache this layer between code changes.
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Add the migration configuration and application source.
COPY alembic.ini .
COPY migrations ./migrations
COPY app ./app

# Run schema migrations before starting the HTTP server.
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]