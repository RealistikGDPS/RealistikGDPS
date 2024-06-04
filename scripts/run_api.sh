#!/bin/bash
set -euo pipefail

echo "Starting server..."

exec uvicorn rgdps.main:asgi_app \
    --host $APP_HOST \
    --port $APP_PORT \
    --no-access-log \
    --reload