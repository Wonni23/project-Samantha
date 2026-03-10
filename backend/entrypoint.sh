#!/bin/sh

echo "Running migrations..."
alembic upgrade head

echo "Starting application..."

if [ -f /app/certs/localhost.pem ] && [ -f /app/certs/localhost-key.pem ]; then
    echo "Starting HTTPS server..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile /app/certs/localhost-key.pem --ssl-certfile /app/certs/localhost.pem --reload
else
    echo "SSL certificates not found, starting HTTP server..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi
