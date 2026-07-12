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


def prefer_local_solving_source():
    for source_path in solving_source_candidates():
        if not (source_path / SOLVING_PACKAGE / "__init__.py").is_file():
            continue
        source_text = str(source_path)
        sys.path[:] = [path for path in sys.path if path != source_text]
        sys.path.insert(0, source_text)
        return source_text
    return None
