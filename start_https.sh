#!/bin/bash
# MakerMatrix HTTPS Startup Script

echo "🚀 Starting MakerMatrix with HTTPS..."

# Activate virtual environment
if [ -f "venv_test/bin/activate" ]; then
    source venv_test/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found at venv_test/bin/activate"
    exit 1
fi

# Set HTTPS environment
export HTTPS_ENABLED=true

# Start the application
python -m MakerMatrix.main

echo "🔒 MakerMatrix is running at https://localhost:8443"
echo "📝 API documentation: https://localhost:8443/docs"
