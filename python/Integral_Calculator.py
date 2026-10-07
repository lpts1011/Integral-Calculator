'''
Post-Release Updates:
'''

import multiprocessing
import os
import sys
from importlib.util import find_spec
from pathlib import Path

from local_source_paths import prefer_local_solving_source


LOCAL_SOLVING_SOURCE = prefer_local_solving_source()


def _relaunch_with_supported_python():
    if find_spec("PySide6") is not None:
        return

    candidates = (
        Path.home() / ".venvs" / "integral-calculator" / "bin" / "python",
        Path(__file__).resolve().parent / ".venv" / "bin" / "python",
    )
    current_python = Path(sys.executable).absolute()
    for candidate in candidates:
        if candidate.is_file() and current_python != candidate.absolute():
            os.execv(
                str(candidate),
                [str(candidate), str(Path(__file__).resolve()), *sys.argv[1:]],
            )


def main():
    _relaunch_with_supported_python()
    if "--self-test" in sys.argv:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
        os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")
        from runtime_self_test import run
        return run()
    from qt_app import main as run_app

    return run_app()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
