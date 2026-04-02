#!/bin/bash
# ============================================
# Flow App - Prepare runtimes for macOS (arm64)
# Downloads and sets up: Node.js, Python, FFmpeg, Playwright Chromium
# ============================================

set -euo pipefail

BUILD_DIR="${1:-./build-mac}"
NODE_VERSION="${NODE_VERSION:-22.14.0}"
PYTHON_VERSION="${PYTHON_VERSION:-3.12.9}"
PYTHON_BUILD_DATE="${PYTHON_BUILD_DATE:-20250317}"

echo "=== Flow App: Preparing runtimes (macOS) ==="
echo "Build dir: $BUILD_DIR"
echo "Node.js: $NODE_VERSION"
echo "Python: $PYTHON_VERSION"
echo ""

mkdir -p "$BUILD_DIR"

# Detect architecture
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    NODE_ARCH="arm64"
    PYTHON_ARCH="aarch64"
elif [ "$ARCH" = "x86_64" ]; then
    NODE_ARCH="x64"
    PYTHON_ARCH="x86_64"
else
    echo "[ERROR] Unsupported architecture: $ARCH"
    exit 1
fi
echo "Architecture: $ARCH ($NODE_ARCH)"
echo ""

# ============================================
# 1. Node.js Portable
# ============================================
echo "--- [1/4] Node.js portable ---"

NODE_DIR="$BUILD_DIR/node"
if [ ! -x "$NODE_DIR/bin/node" ]; then
    NODE_URL="https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-darwin-${NODE_ARCH}.tar.gz"
    NODE_TAR="$BUILD_DIR/node.tar.gz"

    echo "Downloading Node.js v$NODE_VERSION..."
    curl -L -o "$NODE_TAR" "$NODE_URL"

    echo "Extracting..."
    tar -xzf "$NODE_TAR" -C "$BUILD_DIR"
    rm -rf "$NODE_DIR"
    mv "$BUILD_DIR"/node-v*-darwin-* "$NODE_DIR"
    rm -f "$NODE_TAR"

    # Remove quarantine
    xattr -cr "$NODE_DIR" 2>/dev/null || true

    echo "Node.js OK: $("$NODE_DIR/bin/node" --version)"
else
    echo "Node.js already prepared."
fi

# ============================================
# 2. Python Standalone
# ============================================
echo ""
echo "--- [2/4] Python standalone ---"

PYTHON_DIR="$BUILD_DIR/python"
if [ ! -x "$PYTHON_DIR/bin/python3" ]; then
    PYTHON_URL="https://github.com/indygreg/python-build-standalone/releases/download/${PYTHON_BUILD_DATE}/cpython-${PYTHON_VERSION}+${PYTHON_BUILD_DATE}-${PYTHON_ARCH}-apple-darwin-install_only.tar.gz"
    PYTHON_TAR="$BUILD_DIR/python.tar.gz"

    echo "Downloading Python $PYTHON_VERSION standalone..."
    curl -L -o "$PYTHON_TAR" "$PYTHON_URL"

    echo "Extracting..."
    rm -rf "$PYTHON_DIR"
    tar -xzf "$PYTHON_TAR" -C "$BUILD_DIR"
    rm -f "$PYTHON_TAR"

    # Remove quarantine
    xattr -cr "$PYTHON_DIR" 2>/dev/null || true

    echo "Python OK: $("$PYTHON_DIR/bin/python3" --version)"

    # Install bot dependencies
    echo "Installing playwright and boto3..."
    "$PYTHON_DIR/bin/python3" -m pip install --quiet playwright boto3
else
    echo "Python already prepared."
fi

# ============================================
# 3. Playwright Chromium
# ============================================
echo ""
echo "--- [3/4] Playwright Chromium ---"

CHROMIUM_DIR="$BUILD_DIR/chromium"
if [ ! -d "$CHROMIUM_DIR" ] || [ -z "$(ls -A "$CHROMIUM_DIR" 2>/dev/null)" ]; then
    echo "Installing Playwright Chromium..."
    mkdir -p "$CHROMIUM_DIR"
    PLAYWRIGHT_BROWSERS_PATH="$CHROMIUM_DIR" "$PYTHON_DIR/bin/python3" -m playwright install chromium
    echo "Chromium OK"
else
    echo "Chromium already installed."
fi

# ============================================
# 4. FFmpeg
# ============================================
echo ""
echo "--- [4/4] FFmpeg ---"

FFMPEG_DIR="$BUILD_DIR/ffmpeg"
if [ ! -x "$FFMPEG_DIR/ffmpeg" ]; then
    mkdir -p "$FFMPEG_DIR"

    echo "Downloading FFmpeg..."
    FFMPEG_ZIP="$BUILD_DIR/ffmpeg.zip"
    curl -L -o "$FFMPEG_ZIP" "https://evermeet.cx/ffmpeg/getrelease/zip"

    echo "Extracting ffmpeg..."
    unzip -o -q "$FFMPEG_ZIP" -d "$FFMPEG_DIR"
    rm -f "$FFMPEG_ZIP"

    echo "Downloading FFprobe..."
    FFPROBE_ZIP="$BUILD_DIR/ffprobe.zip"
    curl -L -o "$FFPROBE_ZIP" "https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip"

    echo "Extracting ffprobe..."
    unzip -o -q "$FFPROBE_ZIP" -d "$FFMPEG_DIR"
    rm -f "$FFPROBE_ZIP"

    chmod +x "$FFMPEG_DIR/ffmpeg" "$FFMPEG_DIR/ffprobe"

    # Remove quarantine
    xattr -cr "$FFMPEG_DIR" 2>/dev/null || true

    echo "FFmpeg OK: $("$FFMPEG_DIR/ffmpeg" -version 2>&1 | head -1)"
else
    echo "FFmpeg already prepared."
fi

# ============================================
# Summary
# ============================================
echo ""
echo "=== Runtimes ready ==="

du_mb() {
    du -sm "$1" 2>/dev/null | awk '{print $1}'
}

echo "  Node.js:  $(du_mb "$BUILD_DIR/node") MB"
echo "  Python:   $(du_mb "$BUILD_DIR/python") MB"
echo "  Chromium: $(du_mb "$BUILD_DIR/chromium") MB"
echo "  FFmpeg:   $(du_mb "$BUILD_DIR/ffmpeg") MB"
echo "  TOTAL:    $(du_mb "$BUILD_DIR") MB"
