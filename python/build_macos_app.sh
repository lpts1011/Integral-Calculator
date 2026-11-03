#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"
APP_VERSION="${APP_VERSION:-6.0}"
MACOS_SIGNING_IDENTITY="${MACOS_SIGNING_IDENTITY:--}"
MACOS_ENTITLEMENTS="${MACOS_ENTITLEMENTS:-macos_distribution.entitlements}"

if [[ ! "$APP_VERSION" =~ ^[0-9]+\.[0-9]+$ ]]; then
    echo "APP_VERSION must be MAJOR.MINOR, for example 6.0: $APP_VERSION"
    exit 1
fi

if [[ "$MACOS_SIGNING_IDENTITY" != "-" ]]; then
    if [[ ! -f "$MACOS_ENTITLEMENTS" ]]; then
        echo "Missing macOS distribution entitlements: $MACOS_ENTITLEMENTS"
        exit 1
    fi
    if ! security find-identity -v -p codesigning | \
        grep -Fq "$MACOS_SIGNING_IDENTITY"; then
        echo "Code-signing identity is not installed: $MACOS_SIGNING_IDENTITY"
        exit 1
    fi
fi

export APP_VERSION

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

EXISTING_WEBENGINE_VERSIONS="dist/Integral_Calculator_Python.app/Contents/Frameworks/PySide6/Qt/lib/QtWebEngineCore.framework/Versions"
if [[ -d "$EXISTING_WEBENGINE_VERSIONS" ]]; then
    chmod u+w "$EXISTING_WEBENGINE_VERSIONS"
fi

"$PYTHON_BIN" -m PyInstaller --clean --noconfirm macos_app.spec

APP_PATH="dist/Integral_Calculator_Python.app"
WEBENGINE_FRAMEWORK="$APP_PATH/Contents/Frameworks/PySide6/Qt/lib/QtWebEngineCore.framework"
WEBENGINE_VERSIONS="$WEBENGINE_FRAMEWORK/Versions"
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

# Qt WebEngine can recreate the invalid empty Versions/Resources directory on
# first launch. Framework bundles are runtime resources, so keep this directory
# read-only after normalizing the version layout.
if [[ -d "$WEBENGINE_VERSIONS" ]]; then
    chmod 0555 "$WEBENGINE_VERSIONS"
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
    cleanup_signing_dir() {
        if [[ -d "$SIGNING_DIR" ]]; then
            find "$SIGNING_DIR" -type d -exec chmod u+w {} + 2>/dev/null || true
            rm -rf "$SIGNING_DIR"
        fi
    }
    trap cleanup_signing_dir EXIT
    SIGNING_APP="$SIGNING_DIR/Integral_Calculator_Python.app"
    ditto --norsrc "$APP_PATH" "$SIGNING_APP"
    if command -v xattr >/dev/null 2>&1; then
        xattr -cr "$SIGNING_APP"
    fi
    if [[ "$MACOS_SIGNING_IDENTITY" == "-" ]]; then
        codesign --force --deep --sign - "$SIGNING_APP"
    else
        codesign \
            --force \
            --deep \
            --options runtime \
            --timestamp \
            --entitlements "$MACOS_ENTITLEMENTS" \
            --sign "$MACOS_SIGNING_IDENTITY" \
            "$SIGNING_APP"
    fi
    codesign --verify --deep --strict "$SIGNING_APP"

    if [[ "$INSTALLED_APP" != *.app ]] || \
        [[ "$INSTALLED_APP" == "/" ]] || \
        [[ "$INSTALLED_APP" == "$HOME" ]] || \
        [[ "$INSTALLED_APP" == "$HOME/Applications" ]]; then
        echo "Unsafe application install path: $INSTALLED_APP"
        exit 1
    fi
    mkdir -p "$(dirname "$INSTALLED_APP")"
    INSTALLED_WEBENGINE_VERSIONS="$INSTALLED_APP/Contents/Frameworks/PySide6/Qt/lib/QtWebEngineCore.framework/Versions"
    if [[ -d "$INSTALLED_WEBENGINE_VERSIONS" ]]; then
        chmod u+w "$INSTALLED_WEBENGINE_VERSIONS"
    fi
    rm -rf "$INSTALLED_APP"
    ditto --norsrc "$SIGNING_APP" "$INSTALLED_APP"
    if [[ -d "$INSTALLED_WEBENGINE_VERSIONS" ]]; then
        chmod 0555 "$INSTALLED_WEBENGINE_VERSIONS"
    fi
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
echo "Version: $APP_VERSION"
echo "Signing identity: $MACOS_SIGNING_IDENTITY"
