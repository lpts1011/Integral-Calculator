"""PyInstaller must collect Windows NumPy, not vendored macOS extensions."""
import sys
from pathlib import Path


def pre_find_module_path(api):
    if sys.platform != "win32":
        return
    project_root = Path(__file__).resolve().parents[2]
    api.search_dirs = [
        directory for directory in api.search_dirs
        if Path(directory).resolve() != project_root
    ]
