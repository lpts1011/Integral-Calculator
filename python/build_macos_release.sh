#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

APP_VERSION="${APP_VERSION:-5.0.1}"
DEVELOPER_ID_APPLICATION="${DEVELOPER_ID_APPLICATION:-}"
NOTARY_PROFILE="${NOTARY_PROFILE:-integral-calculator-notary}"
RELEASE_DIR="${RELEASE_DIR:-$PWD/release}"
INSTALLED_APP="${INTEGRAL_CALCULATOR_APP_PATH:-$HOME/Applications/Integral_Calculator_Python.app}"

if [[ ! "$APP_VERSION" =~ ^[0-9]+(\.[0-9]+){0,2}$ ]]; then
    echo "APP_VERSION must contain one to three numeric components: $APP_VERSION"
    exit 1
fi

for tool in codesign ditto hdiutil lipo security shasum spctl xcrun; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "Missing required macOS release tool: $tool"
        exit 1
    fi
done

if [[ -z "$DEVELOPER_ID_APPLICATION" ]]; then
    echo "DEVELOPER_ID_APPLICATION is required."
    echo 'Example: Developer ID Application: Your Name (TEAMID)'
    exit 1
fi

if ! security find-identity -v -p codesigning | \
    grep -Fq "$DEVELOPER_ID_APPLICATION"; then
    echo "Developer ID certificate is not installed: $DEVELOPER_ID_APPLICATION"
    exit 1
fi

if ! xcrun notarytool history \
    --keychain-profile "$NOTARY_PROFILE" >/dev/null 2>&1; then
    echo "Notary credentials are unavailable for profile: $NOTARY_PROFILE"
    echo "Configure them with: xcrun notarytool store-credentials"
    exit 1
fi

APP_VERSION="$APP_VERSION" \
MACOS_SIGNING_IDENTITY="$DEVELOPER_ID_APPLICATION" \
MACOS_ENTITLEMENTS="macos_distribution.entitlements" \
./build_macos_app.sh

codesign --verify --deep --strict "$INSTALLED_APP"

APP_EXECUTABLE="$INSTALLED_APP/Contents/MacOS/Integral_Calculator_Python"
ARCHITECTURES="$(lipo -archs "$APP_EXECUTABLE")"
case "$ARCHITECTURES" in
    arm64)
        ARCH_LABEL="arm64"
        ;;
    x86_64)
        ARCH_LABEL="x86_64"
        ;;
    *arm64*x86_64*|*x86_64*arm64*)
        ARCH_LABEL="universal2"
        ;;
    *)
        ARCH_LABEL="${ARCHITECTURES// /-}"
        ;;
esac

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/integral-calculator-release.XXXXXX")"
trap 'rm -rf "$WORK_DIR"' EXIT

DMG_ROOT="$WORK_DIR/dmg-root"
mkdir -p "$DMG_ROOT"
ditto --norsrc "$INSTALLED_APP" "$DMG_ROOT/Integral Calculator.app"
ln -s /Applications "$DMG_ROOT/Applications"

DMG_NAME="Integral-Calculator-Python-macOS-${ARCH_LABEL}-v${APP_VERSION}.dmg"
STAGED_DMG="$WORK_DIR/$DMG_NAME"
OUTPUT_DMG="$RELEASE_DIR/$DMG_NAME"

hdiutil create \
    -quiet \
    -volname "Integral Calculator" \
    -srcfolder "$DMG_ROOT" \
    -format UDZO \
    -ov \
    "$STAGED_DMG"

codesign \
    --force \
    --sign "$DEVELOPER_ID_APPLICATION" \
    --timestamp \
    "$STAGED_DMG"

xcrun notarytool submit "$STAGED_DMG" \
    --keychain-profile "$NOTARY_PROFILE" \
    --wait
xcrun stapler staple "$STAGED_DMG"
xcrun stapler validate "$STAGED_DMG"
codesign --verify --strict "$STAGED_DMG"
spctl --assess \
    --type open \
    --context context:primary-signature \
    --verbose=4 \
    "$STAGED_DMG"

mkdir -p "$RELEASE_DIR"
if [[ -e "$OUTPUT_DMG" ]]; then
    echo "Refusing to overwrite existing release: $OUTPUT_DMG"
    exit 1
fi
ditto --norsrc "$STAGED_DMG" "$OUTPUT_DMG"

echo
echo "Notarized release: $OUTPUT_DMG"
echo "Architectures: $ARCHITECTURES"
shasum -a 256 "$OUTPUT_DMG"
