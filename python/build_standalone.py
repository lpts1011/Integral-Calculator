#!/usr/bin/env python3
"""Build the source and native-runtime single-file Integral Calculator."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import os
import stat
import tarfile
import tempfile
import textwrap
import zipfile
from pathlib import Path


MAIN_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = MAIN_DIR.parent / "Integral_Calculator_Standalone.py"
DEFAULT_APP = Path.home() / "Applications" / "Integral_Calculator_Python.app"
APP_PAYLOAD_MARKER = "# __INTEGRAL_CALCULATOR_APP_PAYLOAD_V1__"
EXCLUDED_DIRECTORIES = {".venv", "__pycache__", "build", "dist", "release", ".ruff_cache"}
EXCLUDED_FILES = {".DS_Store"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


LAUNCHER_TEMPLATE = '''#!/usr/bin/env python3
"""
Self-contained Integral Calculator launcher for Apple-silicon Macs.

This file embeds the complete current Main source tree and a signed native
application runtime. When the active Python already has PySide6 and Matplotlib,
the embedded source runs directly. Otherwise, the launcher extracts and starts
its own arm64 macOS application without using an external Main folder or Python
package installation.
"""

from pathlib import Path
import base64
import hashlib
import importlib.util
import io
import os
import platform
import runpy
import shutil
import sys
import tarfile
import zipfile

_BUNDLE_SHA256 = "__BUNDLE_SHA256__"
_BUNDLE_FILE_COUNT = __BUNDLE_FILE_COUNT__
_APP_BUNDLE_SHA256 = "__APP_BUNDLE_SHA256__"
_APP_BUNDLE_SIZE = __APP_BUNDLE_SIZE__
_APP_BUNDLE_NAME = "Integral_Calculator_Python.app"
_APP_PAYLOAD_MARKER = b"__APP_PAYLOAD_MARKER__"
_BUNDLE_CACHE_NAME = "integral_calculator_standalone"
_BUNDLE_PAYLOAD = (
__BUNDLE_PAYLOAD__
)


def _cache_root():
    override = os.environ.get("INTEGRAL_CALCULATOR_STANDALONE_CACHE")
    if override:
        return Path(override).expanduser()
    return Path.home() / f".{_BUNDLE_CACHE_NAME}"


def _decode_payload():
    data = base64.b64decode(_BUNDLE_PAYLOAD.encode("ascii"))
    actual = hashlib.sha256(data).hexdigest()
    if actual != _BUNDLE_SHA256:
        raise RuntimeError("Standalone source bundle is corrupted.")
    return data


def _prune_old_caches(current_cache):
    cache_root = current_cache.parent
    if not cache_root.is_dir():
        return
    for candidate in cache_root.iterdir():
        if candidate == current_cache or not candidate.is_dir():
            continue
        if (candidate / ".bundle-complete").is_file():
            shutil.rmtree(candidate, ignore_errors=True)


def _safe_extract_zip(zip_file, target_dir):
    target_root = target_dir.resolve()
    for member in zip_file.infolist():
        destination = (target_dir / member.filename).resolve()
        if target_root != destination and target_root not in destination.parents:
            raise RuntimeError(f"Unsafe path inside source bundle: {member.filename}")
    zip_file.extractall(target_dir)


def _safe_extract_tar(tar_file, target_dir):
    target_root = target_dir.resolve()
    for member in tar_file.getmembers():
        destination = (target_dir / member.name).resolve()
        if target_root != destination and target_root not in destination.parents:
            raise RuntimeError(f"Unsafe path inside app bundle: {member.name}")
        if member.issym():
            link_target = (destination.parent / member.linkname).resolve()
        elif member.islnk():
            link_target = (target_dir / member.linkname).resolve()
        else:
            continue
        if target_root != link_target and target_root not in link_target.parents:
            raise RuntimeError(f"Unsafe link inside app bundle: {member.name}")
    tar_file.extractall(target_dir, filter="data")


def _extract_source_bundle():
    cache_dir = _cache_root() / _BUNDLE_SHA256[:16]
    marker = cache_dir / ".bundle-complete"
    main_dir = cache_dir / "Main"
    entrypoint = main_dir / "Integral_Calculator.py"
    if (
        marker.is_file()
        and marker.read_text(encoding="utf-8") == _BUNDLE_SHA256
        and entrypoint.is_file()
    ):
        _prune_old_caches(cache_dir)
        return cache_dir, main_dir
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(_decode_payload())) as zip_file:
        if len(zip_file.infolist()) != _BUNDLE_FILE_COUNT:
            raise RuntimeError("Standalone source bundle has the wrong file count.")
        _safe_extract_zip(zip_file, cache_dir)
    marker.write_text(_BUNDLE_SHA256, encoding="utf-8")
    _prune_old_caches(cache_dir)
    return cache_dir, main_dir


def _copy_embedded_app_archive(destination):
    digest = hashlib.sha256()
    written = 0
    found = False
    with Path(__file__).open("rb") as source, destination.open("wb") as output:
        for line in source:
            if line.rstrip(b"\\r\\n") == _APP_PAYLOAD_MARKER:
                found = True
                break
        if not found:
            raise RuntimeError("Embedded application payload marker is missing.")
        for line in source:
            encoded = line.strip()
            if not encoded:
                continue
            if not encoded.startswith(b"# "):
                raise RuntimeError("Embedded application payload is malformed.")
            chunk = base64.b64decode(encoded[2:], validate=True)
            digest.update(chunk)
            output.write(chunk)
            written += len(chunk)
    if written != _APP_BUNDLE_SIZE or digest.hexdigest() != _APP_BUNDLE_SHA256:
        destination.unlink(missing_ok=True)
        raise RuntimeError("Embedded application payload is corrupted.")


def _protect_embedded_webengine_layout(app_dir):
    versions = (
        app_dir
        / "Contents"
        / "Frameworks"
        / "PySide6"
        / "Qt"
        / "lib"
        / "QtWebEngineCore.framework"
        / "Versions"
    )
    if not versions.is_dir():
        raise RuntimeError("Embedded Qt WebEngine framework is missing.")
    invalid_version = versions / "Resources"
    if invalid_version.is_symlink() or (
        invalid_version.exists() and not invalid_version.is_dir()
    ):
        raise RuntimeError("Embedded Qt WebEngine framework layout is invalid.")
    if invalid_version.is_dir():
        if any(invalid_version.iterdir()):
            raise RuntimeError("Embedded Qt WebEngine framework layout is invalid.")
        os.chmod(versions, 0o755)
        invalid_version.rmdir()
    os.chmod(versions, 0o555)


def _extract_embedded_app(cache_dir):
    runtime_dir = cache_dir / "embedded-runtime"
    app_dir = runtime_dir / _APP_BUNDLE_NAME
    executable = app_dir / "Contents" / "MacOS" / "Integral_Calculator_Python"
    marker = runtime_dir / ".app-complete"
    if (
        marker.is_file()
        and marker.read_text(encoding="utf-8") == _APP_BUNDLE_SHA256
        and executable.is_file()
    ):
        _protect_embedded_webengine_layout(app_dir)
        return app_dir

    archive_path = cache_dir / ".embedded-app.tar.gz"
    temporary_dir = cache_dir / ".embedded-runtime.tmp"
    archive_path.unlink(missing_ok=True)
    if temporary_dir.exists():
        shutil.rmtree(temporary_dir)
    temporary_dir.mkdir(parents=True)
    try:
        _copy_embedded_app_archive(archive_path)
        with tarfile.open(archive_path, "r:gz") as tar_file:
            _safe_extract_tar(tar_file, temporary_dir)
        temporary_app = temporary_dir / _APP_BUNDLE_NAME
        _protect_embedded_webengine_layout(temporary_app)
        temporary_executable = (
            temporary_app
            / "Contents"
            / "MacOS"
            / "Integral_Calculator_Python"
        )
        if not temporary_executable.is_file():
            raise RuntimeError("Embedded application executable is missing.")
        if runtime_dir.exists():
            shutil.rmtree(runtime_dir)
        temporary_dir.replace(runtime_dir)
        marker.write_text(_APP_BUNDLE_SHA256, encoding="utf-8")
    finally:
        archive_path.unlink(missing_ok=True)
        if temporary_dir.exists():
            shutil.rmtree(temporary_dir)
    return app_dir


def _missing_gui_dependencies():
    return tuple(
        name
        for name in ("PySide6", "matplotlib")
        if importlib.util.find_spec(name) is None
    )


def _embedded_runtime_supported():
    return sys.platform == "darwin" and platform.machine() == "arm64"


def _launch_embedded_app(cache_dir):
    app_dir = _extract_embedded_app(cache_dir)
    executable = app_dir / "Contents" / "MacOS" / "Integral_Calculator_Python"
    print("Starting the embedded Integral Calculator runtime...", file=sys.stderr)
    os.execv(str(executable), [str(executable)])


def _self_test(cache_dir, main_dir):
    required = (
        "Integral_Calculator.py",
        "qt_app.py",
        "qt_main_window.py",
        "qt_math_keyboard.py",
        "qt_result_workspace.py",
        "math_editor/resources/editor.html",
        "math_editor/resources/results.html",
    )
    missing_files = [name for name in required if not (main_dir / name).is_file()]
    if missing_files:
        raise RuntimeError(f"Standalone bundle is missing: {', '.join(missing_files)}")

    import calengine as np
    from solving.integrals.integrals import integrate

    missing_dependencies = _missing_gui_dependencies()
    if missing_dependencies:
        if not _embedded_runtime_supported():
            names = ", ".join(missing_dependencies)
            raise RuntimeError(f"Missing runtime dependencies: {names}")
        app_dir = _extract_embedded_app(cache_dir)
        entrypoint = app_dir / "Contents" / "MacOS" / "Integral_Calculator_Python"
    else:
        from qt_app import main as qt_main

        entrypoint = f"{qt_main.__module__}.{qt_main.__name__}"

    print("Standalone bundle OK")
    print(f"files={_BUNDLE_FILE_COUNT}")
    print(f"bundle={_BUNDLE_SHA256}")
    print(f"main_dir={main_dir}")
    print(f"numpy={getattr(np, '__file__', 'unknown')}")
    print(f"integrate_module={integrate.__module__}")
    print(f"entrypoint={entrypoint}")


def main():
    cache_dir, main_dir = _extract_source_bundle()
    sys.path.insert(0, str(main_dir))
    os.chdir(main_dir)
    if "--self-test" in sys.argv:
        _self_test(cache_dir, main_dir)
        return

    missing_dependencies = _missing_gui_dependencies()
    if missing_dependencies:
        if _embedded_runtime_supported():
            _launch_embedded_app(cache_dir)
        names = ", ".join(missing_dependencies)
        raise RuntimeError(
            f"Missing runtime dependencies: {names}. "
            "The embedded native runtime supports Apple-silicon Macs."
        )
    runpy.run_path(str(main_dir / "Integral_Calculator.py"), run_name="__main__")


if __name__ == "__main__":
    main()
'''


def iter_bundle_files(main_dir: Path = MAIN_DIR):
    """Yield all source files needed by the standalone bundle in stable order."""
    candidates = sorted(
        main_dir.rglob("*"),
        key=lambda path: path.relative_to(main_dir).as_posix(),
    )
    for path in candidates:
        relative = path.relative_to(main_dir)
        if path.is_symlink() or not path.is_file():
            continue
        if any(part in EXCLUDED_DIRECTORIES for part in relative.parts):
            continue
        if any(part.endswith(".app") for part in relative.parts):
            continue
        if path.name in EXCLUDED_FILES or path.suffix in EXCLUDED_SUFFIXES:
            continue
        yield path


def _archive_info(path: Path, archive_name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(archive_name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    mode = stat.S_IMODE(path.stat().st_mode)
    info.external_attr = (stat.S_IFREG | mode) << 16
    return info


def build_source_archive(main_dir: Path = MAIN_DIR):
    files = list(iter_bundle_files(main_dir))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for path in files:
            relative = path.relative_to(main_dir).as_posix()
            info = _archive_info(path, f"Main/{relative}")
            zip_file.writestr(info, path.read_bytes(), compresslevel=9)
    return buffer.getvalue(), files


def _normalize_tar_info(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    info.pax_headers = {}
    return info


def build_app_archive(app_path: Path, destination: Path) -> tuple[str, int]:
    executable = app_path / "Contents" / "MacOS" / "Integral_Calculator_Python"
    if not executable.is_file():
        raise FileNotFoundError(f"Signed macOS app not found: {app_path}")
    with destination.open("wb") as raw_file:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            compresslevel=9,
            fileobj=raw_file,
            mtime=0,
        ) as gzip_file:
            with tarfile.open(
                fileobj=gzip_file,
                mode="w",
                format=tarfile.PAX_FORMAT,
                dereference=False,
            ) as tar_file:
                tar_file.add(
                    app_path,
                    arcname=app_path.name,
                    recursive=True,
                    filter=_normalize_tar_info,
                )
    return _file_sha256(destination), destination.stat().st_size


def render_launcher(main_dir: Path, app_sha256: str, app_size: int) -> str:
    archive, files = build_source_archive(main_dir)
    encoded = base64.b64encode(archive).decode("ascii")
    payload = "\n".join(
        f'    "{chunk}"' for chunk in textwrap.wrap(encoded, width=12_000)
    )
    return (
        LAUNCHER_TEMPLATE.replace(
            "__BUNDLE_SHA256__", hashlib.sha256(archive).hexdigest()
        )
        .replace("__BUNDLE_FILE_COUNT__", str(len(files)))
        .replace("__APP_BUNDLE_SHA256__", app_sha256)
        .replace("__APP_BUNDLE_SIZE__", str(app_size))
        .replace("__APP_PAYLOAD_MARKER__", APP_PAYLOAD_MARKER)
        .replace("__BUNDLE_PAYLOAD__", payload)
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _files_equal(left: Path, right: Path) -> bool:
    return (
        left.is_file()
        and right.is_file()
        and left.stat().st_size == right.stat().st_size
        and _file_sha256(left) == _file_sha256(right)
    )


def _write_app_payload(output, app_archive: Path) -> None:
    output.write((APP_PAYLOAD_MARKER + "\n").encode("ascii"))
    with app_archive.open("rb") as source:
        for chunk in iter(lambda: source.read(9_000), b""):
            output.write(b"# " + base64.b64encode(chunk) + b"\n")


def generate_candidate(
    output: Path,
    app_path: Path = DEFAULT_APP,
    main_dir: Path = MAIN_DIR,
) -> Path:
    candidate = output.with_suffix(output.suffix + ".tmp")
    candidate.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="integral-standalone-") as temp_dir:
        app_archive = Path(temp_dir) / "Integral_Calculator_Python.app.tar.gz"
        app_sha256, app_size = build_app_archive(app_path, app_archive)
        launcher = render_launcher(main_dir, app_sha256, app_size)
        with candidate.open("wb") as generated_file:
            generated_file.write(launcher.encode("utf-8"))
            generated_file.write(b"\n")
            _write_app_payload(generated_file, app_archive)
    os.chmod(candidate, 0o755)
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if output is stale")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--app", type=Path, default=DEFAULT_APP)
    args = parser.parse_args()

    candidate = generate_candidate(args.output, args.app)
    try:
        current = _files_equal(args.output, candidate)
        if args.check:
            if not current:
                print(f"Standalone bundle is stale: {args.output}")
                return 1
            print(f"Standalone bundle is current: {args.output}")
            return 0
        if current:
            print(f"Already current: {args.output}")
            return 0
        candidate.replace(args.output)
        print(f"Updated: {args.output}")
        return 0
    finally:
        candidate.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
