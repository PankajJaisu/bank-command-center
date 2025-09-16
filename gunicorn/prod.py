# gunicorn/prod.py
"""Gunicorn *production* config file"""

import os
import sys
import multiprocessing

# Ensure the src directory is in the Python path
# Try multiple possible paths for Render deployment
possible_src_paths = [
    "/opt/render/project/src",
    os.path.join(os.getcwd(), "src"),
    os.path.join(os.path.dirname(__file__), "..", "src")
]

for src_path in possible_src_paths:
    if os.path.exists(src_path) and src_path not in sys.path:
        sys.path.insert(0, src_path)
        print(f"Added {src_path} to Python path")
        break

# Also try to add PYTHONPATH from environment
pythonpath = os.environ.get('PYTHONPATH')
if pythonpath:
    for path in pythonpath.split(':'):
        if path and path not in sys.path:
            sys.path.insert(0, path)
            print(f"Added {path} from PYTHONPATH to sys.path")

# FastAPI ASGI application path
wsgi_app = "app.main:app"

# Logging
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
accesslog = errorlog = "-"  # Log to stdout/stderr for Docker
capture_output = True

# Concurrency and Workers
# Use the WEB_CONCURRENCY env var if set, otherwise calculate based on CPU
workers = 1  # int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = int(os.getenv("WORKER_CONNECTIONS", "1000"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Production settings (no reload, no daemon)
reload = False
daemon = False
