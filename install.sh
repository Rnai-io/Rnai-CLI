#!/bin/sh
# Rnai-CLI installer — ใช้: curl -fsSL https://raw.githubusercontent.com/Rnai-io/Rnai-CLI/main/install.sh | sh
set -e

echo ""
echo "  Installing Rnai-CLI..."
echo ""

PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then
  echo "  ✗ python3 not found — please install Python 3.9+ first"
  echo "    macOS:  https://www.python.org/downloads/  (หรือ brew install python)"
  exit 1
fi

"$PY" -m pip install --user --quiet --upgrade pip 2>/dev/null || true
"$PY" -m pip install --user --quiet "git+https://github.com/Rnai-io/Rnai-CLI.git"

BIN="$("$PY" -m site --user-base)/bin"

echo "  ✓ Rnai-CLI installed"
echo ""
if command -v rnai >/dev/null 2>&1; then
  echo "  เริ่มใช้งาน:  rnai --help"
else
  echo "  เพิ่ม PATH ก่อนใช้งาน (ครั้งเดียว):"
  echo "    echo 'export PATH=\"$BIN:\$PATH\"' >> ~/.zshrc && source ~/.zshrc"
  echo "  แล้วรัน:  rnai --help"
fi
echo ""
