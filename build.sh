#!/bin/bash
# Render build script for Collection Command Center

set -e  # Exit on any error

echo "🚀 Starting Render build process..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r packages/requirements.txt

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p generated_documents
mkdir -p sample_data
chmod 755 generated_documents

# Set PYTHONPATH for the application
export PYTHONPATH="/opt/render/project/src:$PYTHONPATH"

# Run database migrations
echo "🗄️ Running database migrations..."
python -m alembic upgrade head

# Initialize configuration data
echo "⚙️ Initializing configuration data..."
python scripts/init_config_data_simple.py

echo "✅ Build completed successfully!"
