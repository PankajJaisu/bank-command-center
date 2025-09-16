#!/bin/bash
# Startup script for Render deployment with debugging

echo "🚀 Starting Bank Command Center..."
echo "Initial working directory: $(pwd)"

# Ensure we're in the project root directory
cd /opt/render/project || {
    echo "❌ Failed to change to project directory"
    exit 1
}

echo "Project root directory: $(pwd)"
echo "Python path: $PYTHONPATH"
echo "Contents of project root:"
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
# Make sure we're in the project root
cd /opt/render/project
# Test the import with the correct PYTHONPATH
PYTHONPATH="/opt/render/project/src" python -c "
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
echo "Current directory: $(pwd)"
echo "Gunicorn config file exists: $(ls -la gunicorn/prod.py 2>/dev/null || echo 'NOT FOUND')"

# Start gunicorn with more verbose output from the project root
exec gunicorn -c gunicorn/prod.py app.main:app --log-level debug --access-logfile - --error-logfile -
