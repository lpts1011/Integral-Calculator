import json
import os
import sys
from pathlib import Path


def _app_support_dir():
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Integral Calculator"
    if os.name == "nt":
        root = os.environ.get("APPDATA")
        if root:
            return Path(root) / "Integral Calculator"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "integral-calculator"


FAVORITES_FILE = _app_support_dir() / "favorites.json"
LEGACY_FAVORITES_FILE = (
    Path.home() / "Library" / "Application Support" / "Integration Calculator" / "favorites.json"
    if sys.platform == "darwin"
    else None
)

DEFAULT_FAVORITES = [
    "x^2",
    "sin(x)",
    "cos(x)",
    "exp(-x)",
    "exp(-x^2)",
    "1/(1+x^2)",
    "sqrt(1-x^2)",
    "log(x)",
]


def load_favorites(path=FAVORITES_FILE):
    for candidate in _candidate_favorite_files(path):
        try:
            data = json.loads(candidate.read_text())
            favorites = data.get("favorites", [])
            clean = [str(item).strip() for item in favorites if str(item).strip()]
            return _unique(clean + DEFAULT_FAVORITES)
        except Exception:
            pass
    return list(DEFAULT_FAVORITES)


def save_favorites(favorites, path=FAVORITES_FILE):
    clean = _unique([item.strip() for item in favorites if item.strip()])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"favorites": clean}, indent=2))


def _unique(items):
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _candidate_favorite_files(path):
    candidates = [path]
    if LEGACY_FAVORITES_FILE and LEGACY_FAVORITES_FILE != path:
        candidates.append(LEGACY_FAVORITES_FILE)
    return candidates
