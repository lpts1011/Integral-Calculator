#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"

for asset in \
    math_editor/resources/editor.html \
    math_editor/resources/results.html \
    math_editor/resources/mathlive.min.js; do
    if [[ ! -f "$asset" ]]; then
        echo "Missing required live-editor asset: $asset"
        echo "Restore the offline assets with: ./scripts/vendor_mathlive.sh"
        exit 1
    fi
done

if [[ ! -d math_editor/resources/fonts ]] || \
    ! compgen -G "math_editor/resources/fonts/*.woff2" >/dev/null; then
    echo "Missing required MathLive fonts: math_editor/resources/fonts"
    echo "Restore the offline assets with: ./scripts/vendor_mathlive.sh"
    exit 1
fi

if ! "$PYTHON_BIN" -c 'import PySide6, PySide6.QtWebEngineWidgets' >/dev/null 2>&1; then
    echo "PySide6 with Qt WebEngine is not installed for: $PYTHON_BIN"
    echo "Activate the project environment or set PYTHON_BIN to its Python executable."
    exit 1
fi

if ! "$PYTHON_BIN" -m PyInstaller --version >/dev/null 2>&1; then
    echo "PyInstaller is not installed for: $PYTHON_BIN"
    echo "Install it with: $PYTHON_BIN -m pip install pyinstaller"
    exit 1
fi

"$PYTHON_BIN" -m PyInstaller --clean --noconfirm macos_app.spec

APP_PATH="dist/Integral_Calculator_Python.app"
WEBENGINE_FRAMEWORK="$APP_PATH/Contents/Frameworks/PySide6/Qt/lib/QtWebEngineCore.framework"
EXTRA_WEBENGINE_VERSION="$WEBENGINE_FRAMEWORK/Versions/Resources"
CURRENT_WEBENGINE_VERSION="$WEBENGINE_FRAMEWORK/Versions/A"
INSTALLED_APP="${INTEGRAL_CALCULATOR_APP_PATH:-$HOME/Applications/Integral_Calculator_Python.app}"
LOCAL_APP_LINK="Integral_Calculator_Python.app"

# PySide6 6.11 wheels can contain an empty Versions/Resources directory.
# PyInstaller mistakes it for a framework version and duplicates WebEngine
# resources there, producing an invalid framework layout for code signing.
if [[ -d "$CURRENT_WEBENGINE_VERSION" ]] && \
    [[ -d "$EXTRA_WEBENGINE_VERSION" ]]; then
    if [[ -d "$EXTRA_WEBENGINE_VERSION/Resources" ]]; then
        ditto --norsrc \
            "$EXTRA_WEBENGINE_VERSION/Resources" \
            "$CURRENT_WEBENGINE_VERSION/Resources"
    fi
    if [[ -d "$EXTRA_WEBENGINE_VERSION/Helpers" ]]; then
        ditto --norsrc \
            "$EXTRA_WEBENGINE_VERSION/Helpers" \
            "$CURRENT_WEBENGINE_VERSION/Helpers"
    fi
    rm -rf "$EXTRA_WEBENGINE_VERSION"
fi

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
    SIGNING_DIR="$(mktemp -d "${TMPDIR:-/tmp}/integral-calculator-sign.XXXXXX")"
    trap 'rm -rf "$SIGNING_DIR"' EXIT
    SIGNING_APP="$SIGNING_DIR/Integral_Calculator_Python.app"
    ditto --norsrc "$APP_PATH" "$SIGNING_APP"
    if command -v xattr >/dev/null 2>&1; then
        xattr -cr "$SIGNING_APP"
    fi
    codesign --force --deep --sign - "$SIGNING_APP"
    codesign --verify --deep --strict "$SIGNING_APP"

    if [[ "$INSTALLED_APP" != *.app ]] || \
        [[ "$INSTALLED_APP" == "/" ]] || \
        [[ "$INSTALLED_APP" == "$HOME" ]] || \
        [[ "$INSTALLED_APP" == "$HOME/Applications" ]]; then
        echo "Unsafe application install path: $INSTALLED_APP"
        exit 1
    fi
    mkdir -p "$(dirname "$INSTALLED_APP")"
    rm -rf "$INSTALLED_APP"
    ditto --norsrc "$SIGNING_APP" "$INSTALLED_APP"
    codesign --verify --deep --strict "$INSTALLED_APP"

    if [[ -L "$LOCAL_APP_LINK" ]]; then
        rm "$LOCAL_APP_LINK"
    elif [[ -e "$LOCAL_APP_LINK" ]]; then
        echo "Cannot create local app link because $LOCAL_APP_LINK already exists."
        exit 1
    fi
    ln -s "$INSTALLED_APP" "$LOCAL_APP_LINK"
fi

echo
echo "Built package: $APP_PATH"
echo "Signed app: $INSTALLED_APP"
echo "Local launcher: $LOCAL_APP_LINK"
