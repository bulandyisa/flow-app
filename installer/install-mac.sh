#!/bin/bash
# ============================================
# Flow App - macOS Installer
# Собирает проект, загружает рантаймы, устанавливает в ~/FlowApp/
#
# Использование:
#   ./installer/install-mac.sh              # полная установка
#   ./installer/install-mac.sh --skip-build # без пересборки (если уже собрано)
# ============================================

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-$HOME/FlowApp}"
SKIP_BUILD=false

for arg in "$@"; do
    case "$arg" in
        --skip-build) SKIP_BUILD=true ;;
    esac
done

# Determine project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo ""
echo "  ========================================"
echo "   Flow App - macOS Installer"
echo "  ========================================"
echo ""
echo "  Project: $PROJECT_ROOT"
echo "  Install: $INSTALL_DIR"
echo ""

# ============================================
# 1. Prerequisites
# ============================================
echo "=== Step 1: Prerequisites ==="

if [ "$(uname)" != "Darwin" ]; then
    echo "[ERROR] This script is for macOS only."
    exit 1
fi

if ! command -v npm &>/dev/null; then
    echo "[ERROR] npm not found. Please install Node.js first."
    exit 1
fi

echo "OK: macOS $(uname -m), npm $(npm --version)"
echo ""

# ============================================
# 2. Build the application
# ============================================
echo "=== Step 2: Building application ==="

if [ "$SKIP_BUILD" = true ]; then
    echo "Skipped (--skip-build)"
else
    cd "$PROJECT_ROOT"
    echo "Installing dependencies..."
    npm ci
    echo "Building..."
    npm run build
    echo "Build complete."
fi
echo ""

# ============================================
# 3. Prepare runtimes
# ============================================
echo "=== Step 3: Preparing runtimes ==="

RUNTIME_DIR="$SCRIPT_DIR/build-mac"
"$SCRIPT_DIR/prepare-runtimes-mac.sh" "$RUNTIME_DIR"
echo ""

# ============================================
# 4. Bundle app/ directory
# ============================================
echo "=== Step 4: Bundling application code ==="

APP_BUNDLE="$RUNTIME_DIR/app"
rm -rf "$APP_BUNDLE"
mkdir -p "$APP_BUNDLE"

# shared
mkdir -p "$APP_BUNDLE/packages/shared/dist"
cp -r "$PROJECT_ROOT/packages/shared/dist/"* "$APP_BUNDLE/packages/shared/dist/"
cp "$PROJECT_ROOT/packages/shared/package.json" "$APP_BUNDLE/packages/shared/"

# server
mkdir -p "$APP_BUNDLE/packages/server/dist"
cp -r "$PROJECT_ROOT/packages/server/dist/"* "$APP_BUNDLE/packages/server/dist/"
cp "$PROJECT_ROOT/packages/server/package.json" "$APP_BUNDLE/packages/server/"

# Remove workspace dep on @flow-app/shared before npm install
cd "$APP_BUNDLE/packages/server"
"$RUNTIME_DIR/node/bin/node" -e "
    const pkg = require('./package.json');
    delete (pkg.dependencies || {})['@flow-app/shared'];
    require('fs').writeFileSync('./package.json', JSON.stringify(pkg, null, 2));
"
npm install --omit=dev 2>/dev/null || true
cd "$PROJECT_ROOT"

# Link shared into server's node_modules
mkdir -p "$APP_BUNDLE/packages/server/node_modules/@flow-app/shared"
cp -r "$APP_BUNDLE/packages/shared/"* "$APP_BUNDLE/packages/server/node_modules/@flow-app/shared/"

# client
mkdir -p "$APP_BUNDLE/packages/client/dist"
cp -r "$PROJECT_ROOT/packages/client/dist/"* "$APP_BUNDLE/packages/client/dist/"

# bot
mkdir -p "$APP_BUNDLE/bot"
cp "$PROJECT_ROOT/bot/flow_bot.py" "$APP_BUNDLE/bot/"
[ -f "$PROJECT_ROOT/bot/r2_storage.py" ] && cp "$PROJECT_ROOT/bot/r2_storage.py" "$APP_BUNDLE/bot/" || true
[ -f "$PROJECT_ROOT/bot/run_safe.sh" ] && cp "$PROJECT_ROOT/bot/run_safe.sh" "$APP_BUNDLE/bot/" || true

# rules
mkdir -p "$APP_BUNDLE/rules"
cp "$PROJECT_ROOT/rules/"* "$APP_BUNDLE/rules/"

# package.json + version.json
cp "$PROJECT_ROOT/package.json" "$APP_BUNDLE/"
VERSION=$("$RUNTIME_DIR/node/bin/node" -p "require('$PROJECT_ROOT/package.json').version")
echo "{\"version\":\"$VERSION\",\"builtAt\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > "$APP_BUNDLE/version.json"

echo "App bundle ready (v$VERSION)"
echo ""

# ============================================
# 5. Assemble installation directory
# ============================================
echo "=== Step 5: Installing to $INSTALL_DIR ==="

mkdir -p "$INSTALL_DIR"

# Copy runtimes (skip if already exist — they're large)
for RUNTIME in node python chromium ffmpeg; do
    if [ -d "$RUNTIME_DIR/$RUNTIME" ]; then
        if [ ! -d "$INSTALL_DIR/$RUNTIME" ]; then
            echo "  Copying $RUNTIME..."
            cp -r "$RUNTIME_DIR/$RUNTIME" "$INSTALL_DIR/$RUNTIME"
        else
            echo "  $RUNTIME already installed, skipping"
        fi
    fi
done

# App code — always replace (this is what updates change)
echo "  Copying app..."
rm -rf "$INSTALL_DIR/app"
cp -r "$APP_BUNDLE" "$INSTALL_DIR/app"

# Data directories — never overwrite
mkdir -p "$INSTALL_DIR/data/projects" "$INSTALL_DIR/data/sessions"

# Launcher and update-checker
cp "$SCRIPT_DIR/launcher.sh" "$INSTALL_DIR/launcher.sh"
chmod +x "$INSTALL_DIR/launcher.sh"

cp "$SCRIPT_DIR/update-checker.js" "$INSTALL_DIR/update-checker.js"

# FlowApp.command — double-clickable launcher
cat > "$INSTALL_DIR/FlowApp.command" << CMDEOF
#!/bin/bash
cd "$INSTALL_DIR"
./launcher.sh
CMDEOF
chmod +x "$INSTALL_DIR/FlowApp.command"

echo ""

# ============================================
# 6. Done
# ============================================
echo "  ========================================"
echo "   Flow App v$VERSION installed!"
echo "  ========================================"
echo ""
echo "  Location: $INSTALL_DIR"
echo ""
echo "  To run:"
echo "    $INSTALL_DIR/launcher.sh"
echo ""
echo "  Or double-click FlowApp.command in Finder."
echo ""
