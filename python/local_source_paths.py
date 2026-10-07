import os
import sys
from pathlib import Path


SOLVING_SOURCE_ENV = "INTEGRAL_CALCULATOR_SOLVING_SOURCE"
VENDOR_DIRNAME = "vendor"
SOLVING_PACKAGE = "solving"


def _unique_paths(paths):
    seen = set()
    unique = []
    for path in paths:
        path_text = str(path)
        if path_text in seen:
            continue
        seen.add(path_text)
        unique.append(path)
    return unique


def solving_source_candidates():
    candidates = []

    runtime_root = getattr(sys, "_MEIPASS", None)
    if runtime_root:
        candidates.append(Path(runtime_root))
        candidates.append(Path(runtime_root) / VENDOR_DIRNAME)

    current_file = Path(__file__).resolve()
    for parent in current_file.parents:
        candidates.append(parent)
        candidates.append(parent / VENDOR_DIRNAME)

    env_path = os.environ.get(SOLVING_SOURCE_ENV)
    if env_path:
        candidates.append(Path(env_path).expanduser())

    return _unique_paths(candidates)


class _CompatibleNumpyFinder:
    """Use the installed NumPy when the bundled native ABI does not match."""
    def __init__(self, excluded):
        self.excluded = excluded

    def find_spec(self, fullname, path=None, target=None):
        if fullname != "numpy":
            return None
        from importlib.machinery import PathFinder
        paths = [item for item in sys.path if Path(item or os.getcwd()).resolve() not in self.excluded]
        return PathFinder.find_spec(fullname, paths)


def prefer_compatible_numpy():
    if getattr(sys, "frozen", False):
        return
    from importlib.machinery import EXTENSION_SUFFIXES
    excluded = set()
    for root in solving_source_candidates():
        core = root / "numpy" / "_core"
        if not core.is_dir():
            continue
        supported = sys.platform == "darwin" and any(
            (core / ("_multiarray_umath" + suffix)).is_file() for suffix in EXTENSION_SUFFIXES)
        if not supported:
            excluded.add(root.resolve())
    if excluded and not any(isinstance(finder, _CompatibleNumpyFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, _CompatibleNumpyFinder(excluded))


def prefer_local_solving_source():
    prefer_compatible_numpy()
    for source_path in solving_source_candidates():
        if not (source_path / SOLVING_PACKAGE / "__init__.py").is_file():
            continue
        source_text = str(source_path)
        sys.path[:] = [path for path in sys.path if path != source_text]
        sys.path.insert(0, source_text)
        return source_text
    return None
