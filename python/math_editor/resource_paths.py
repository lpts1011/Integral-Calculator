import hashlib
import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path


_RUNTIME_LOCK = threading.Lock()
_RUNTIME_STAGES = {}


def resource_root() -> Path:
    """Return the directory containing the bundled math editor resources."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass is not None:
        return Path(meipass) / "math_editor" / "resources"
    return Path(__file__).resolve().parent / "resources"


def _resource_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        with path.open("rb") as resource:
            for chunk in iter(lambda: resource.read(64 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def runtime_resource_root(cache_root=None) -> Path:
    """Stage editor assets in a private, file-URL-safe runtime directory."""
    source = resource_root()
    version = (source / "mathlive.version").read_text(encoding="utf-8").strip()
    safe_version = "".join(
        character if character.isalnum() or character in ".-_" else "_"
        for character in version
    )
    cache = (
        Path(cache_root)
        if cache_root is not None
        else Path(tempfile.gettempdir()) / "integral-calculator-math-editor"
    )
    if cache.is_symlink():
        raise RuntimeError("Math editor runtime root cannot be a symbolic link.")
    cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    if cache.is_symlink() or not cache.is_dir():
        raise RuntimeError("Math editor runtime root is not a private directory.")
    os.chmod(cache, 0o700)

    expected_digest = _resource_digest(source)
    key = (str(source.resolve()), expected_digest, str(cache.resolve()))

    with _RUNTIME_LOCK:
        existing = _RUNTIME_STAGES.get(key)
        if existing is not None:
            target = Path(existing.name)
            if (
                target.is_symlink()
                or not target.is_dir()
                or _resource_digest(target) != expected_digest
            ):
                raise RuntimeError("Math editor runtime resources were modified.")
            return target

        runtime = tempfile.TemporaryDirectory(
            prefix=f"mathlive-{safe_version}-{expected_digest[:12]}-",
            dir=cache,
        )
        target = Path(runtime.name)
        shutil.copytree(source, target, dirs_exist_ok=True)
        if _resource_digest(target) != expected_digest:
            runtime.cleanup()
            raise RuntimeError("Math editor runtime resources failed verification.")
        _RUNTIME_STAGES[key] = runtime
        return target
