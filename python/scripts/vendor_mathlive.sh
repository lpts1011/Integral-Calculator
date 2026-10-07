#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EXPECTED_VERSION="0.110.0"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

CALLER="$(pwd)"
if [[ -n "${MATHLIVE_DEST:-}" ]]; then
    case "$MATHLIVE_DEST" in
        /*) DEST="$MATHLIVE_DEST" ;;
        *) DEST="$CALLER/$MATHLIVE_DEST" ;;
    esac
else
    DEST="$ROOT/math_editor/resources"
fi
if [[ -n "${MATHLIVE_NOTICE_DEST:-}" ]]; then
    case "$MATHLIVE_NOTICE_DEST" in
        /*) NOTICE_DEST="$MATHLIVE_NOTICE_DEST" ;;
        *) NOTICE_DEST="$CALLER/$MATHLIVE_NOTICE_DEST" ;;
    esac
else
    NOTICE_DEST="$ROOT/THIRD_PARTY_NOTICES"
fi
if [[ -n "${MATHLIVE_TARBALL:-}" ]]; then
    case "$MATHLIVE_TARBALL" in
        /*) ARCHIVE="$MATHLIVE_TARBALL" ;;
        *) ARCHIVE="$CALLER/$MATHLIVE_TARBALL" ;;
    esac
else
    cd "$TMP"
    PACKED_NAME="$(npm pack mathlive@${EXPECTED_VERSION} --silent)"
    ARCHIVE="$TMP/$PACKED_NAME"
fi

mkdir -p "$DEST" "$DEST/fonts" "$NOTICE_DEST"
cd "$TMP"
if [[ ! -f "$ARCHIVE" ]]; then
    printf 'MathLive tarball not found: %s\n' "$ARCHIVE" >&2
    exit 1
fi
tar -xzf "$ARCHIVE"
PACKAGE_VERSION="$(
    python3 - "$TMP/package/package.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as package_file:
    print(json.load(package_file)["version"])
PY
)"
if [[ "$PACKAGE_VERSION" != "$EXPECTED_VERSION" ]]; then
    printf 'MathLive package version must be %s; found %s\n' "$EXPECTED_VERSION" "$PACKAGE_VERSION" >&2
    exit 1
fi
install -m 0644 package/mathlive.min.js "$DEST/mathlive.min.js"
cp -R package/fonts/. "$DEST/fonts/"
install -m 0644 package/LICENSE.txt "$NOTICE_DEST/mathlive_mit_license.txt"
printf '%s\n' "$PACKAGE_VERSION" > "$DEST/mathlive.version"
BUNDLE_SHA256="$(
    python3 - "$DEST/mathlive.min.js" <<'PY'
import hashlib
import sys

with open(sys.argv[1], "rb") as bundle_file:
    print(hashlib.sha256(bundle_file.read()).hexdigest())
PY
)"
printf '%s  mathlive.min.js\n' "$BUNDLE_SHA256" > "$DEST/mathlive.min.js.sha256"
