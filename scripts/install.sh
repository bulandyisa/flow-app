#!/bin/bash
set -e

echo "==================================="
echo "  Installing Flow App"
echo "==================================="
echo ""

# Check Node.js
if ! command -v node &>/dev/null; then
    echo "ERROR: Node.js not found."
    echo "Install from https://nodejs.org (v18+ required)"
    exit 1
fi
echo "Node.js: $(node --version)"

# Check Python
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "ERROR: Python 3 not found."
    echo "Install from https://python.org (v3.9+ required)"
    exit 1
fi
echo "Python: $($PYTHON --version)"

# Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
  echo ""
  echo "Installing FFmpeg..."
  if [[ "$OSTYPE" == "darwin"* ]]; then
    brew install ffmpeg || echo "WARNING: Install FFmpeg manually: brew install ffmpeg"
  else
    sudo apt-get install -y ffmpeg || echo "WARNING: Install FFmpeg manually: apt install ffmpeg"
  fi
else
  echo "FFmpeg: $(ffmpeg -version 2>&1 | head -1)"
fi

# Install npm dependencies
echo ""
echo "Installing npm dependencies..."
npm install

# Install Playwright Chromium
echo ""
echo "Installing Playwright Chromium browser..."
npx playwright install chromium

echo ""
echo "==================================="
echo "  Installation complete!"
echo "  Run: npm run dev"
echo "==================================="
