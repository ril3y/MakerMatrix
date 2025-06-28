#!/bin/bash
# Quick HTTPS Setup for MakerMatrix
# This script sets up HTTPS with self-signed certificates for DigiKey OAuth

echo "🔒 MakerMatrix Quick HTTPS Setup"
echo "================================="

# Check if virtual environment exists
if [ ! -f "venv_test/bin/activate" ]; then
    echo "❌ Virtual environment not found at venv_test/bin/activate"
    echo "   Please run this from the MakerMatrix root directory"
    exit 1
fi

# Activate virtual environment
source venv_test/bin/activate
echo "✅ Virtual environment activated"

# Run HTTPS setup
echo "🔑 Setting up HTTPS with self-signed certificates..."
python scripts/setup_https.py

# Check if setup was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 HTTPS setup complete!"
    echo ""
    echo "🚀 Start MakerMatrix with HTTPS:"
    echo "   ./start_https.sh"
    echo ""
    echo "🔗 Access your app at:"
    echo "   https://localhost:8443"
    echo ""
    echo "⚙️  Configure DigiKey OAuth:"
    echo "   1. Go to https://developer.digikey.com"
    echo "   2. Set redirect URI: https://localhost:8443/digikey_callback"
    echo "   3. Add your credentials in MakerMatrix"
    echo ""
    echo "⚠️  Browser will show security warning - click 'Advanced' → 'Proceed'"
else
    echo "❌ HTTPS setup failed"
    exit 1
fi