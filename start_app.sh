#!/bin/bash
# Startup script for Render deployment with debugging

echo "🚀 Starting Bank Command Center..."
echo "Current working directory: $(pwd)"
echo "Python path: $PYTHONPATH"
echo "Contents of current directory:"
ls -la

echo "Contents of src directory:"
if [ -d "src" ]; then
    ls -la src/
else
    echo "❌ src directory not found in current directory"
fi

echo "Checking for app module:"
if [ -d "src/app" ]; then
    echo "✅ src/app directory found"
    ls -la src/app/
else
    echo "❌ src/app directory not found"
fi

echo "Setting PYTHONPATH and starting gunicorn..."
export PYTHONPATH="/opt/render/project/src:$PYTHONPATH"
echo "Updated PYTHONPATH: $PYTHONPATH"

# Start gunicorn
exec gunicorn -c gunicorn/prod.py app.main:app
