#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! python3 -m PyInstaller --version >/dev/null 2>&1; then
    echo "PyInstaller is not installed for this Python."
    echo "Install it with: python3 -m pip install pyinstaller"
    exit 1
fi

python3 -m PyInstaller --clean --noconfirm macos_app.spec

APP_PATH="dist/Integral Calculator.app"

if command -v dot_clean >/dev/null 2>&1; then
    dot_clean -m "$APP_PATH" 2>/dev/null || true
fi

find "$APP_PATH" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find "$APP_PATH" -type l -name __pycache__ -delete 2>/dev/null || true
find "$APP_PATH" -type f -name '*.pyc' -delete 2>/dev/null || true
find "$APP_PATH" \( -name '.DS_Store' -o -name '._*' \) -delete 2>/dev/null || true

if command -v xattr >/dev/null 2>&1; then
    xattr -cr "$APP_PATH" 2>/dev/null || true
    find "$APP_PATH" -type l -exec xattr -cs {} + 2>/dev/null || true
    for target in "$APP_PATH" "$APP_PATH/Contents/Frameworks/Python.framework" "$APP_PATH/Contents/Resources/Python.framework"; do
        xattr -d com.apple.FinderInfo "$target" 2>/dev/null || true
        xattr -d 'com.apple.fileprovider.fpfs#P' "$target" 2>/dev/null || true
    done
fi

if command -v codesign >/dev/null 2>&1; then
    codesign --remove-signature "$APP_PATH" 2>/dev/null || true
    if command -v xattr >/dev/null 2>&1; then
        xattr -d com.apple.FinderInfo "$APP_PATH" 2>/dev/null || true
        xattr -d 'com.apple.fileprovider.fpfs#P' "$APP_PATH" 2>/dev/null || true
    fi
    codesign --force --deep --sign - "$APP_PATH" || {
        echo "Ad-hoc signing failed. The app was still built, but macOS may ask for manual approval."
    }
fi

echo
echo "Built: $APP_PATH"
