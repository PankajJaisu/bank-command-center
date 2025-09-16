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

echo "Testing Python import..."
cd /opt/render/project/src
python -c "
try:
    from app.main import app
    print('✅ FastAPI app import successful')
    print(f'App type: {type(app)}')
except Exception as e:
    print(f'❌ FastAPI app import failed: {e}')
    import traceback
    traceback.print_exc()
"

echo "Starting gunicorn with verbose logging..."
cd /opt/render/project
# Start gunicorn with more verbose output
exec gunicorn -c gunicorn/prod.py app.main:app --log-level debug --access-logfile - --error-logfile -
