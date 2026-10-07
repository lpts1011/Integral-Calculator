import io
import runpy
import tempfile
import unittest
import zipfile
from pathlib import Path

from build_standalone import MAIN_DIR, iter_bundle_files


STANDALONE_PATH = MAIN_DIR.parent / "Integral_Calculator_Standalone.py"


class StandaloneBundleTests(unittest.TestCase):
    def test_payload_exactly_matches_the_current_main_tree(self):
        if not STANDALONE_PATH.is_file():
            self.skipTest("Standalone launcher is outside this extracted source tree")

        namespace = runpy.run_path(
            str(STANDALONE_PATH), run_name="standalone_parity_check"
        )
        archive = namespace["_decode_payload"]()
        expected = {
            f"Main/{path.relative_to(MAIN_DIR).as_posix()}": path
            for path in iter_bundle_files(MAIN_DIR)
        }
        self.assertFalse(any(".venv" in path.parts for path in expected.values()))

        with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
            actual = set(zip_file.namelist())
            self.assertEqual(actual, set(expected))
            self.assertEqual(namespace["_BUNDLE_FILE_COUNT"], len(expected))
            for name, path in expected.items():
                self.assertEqual(zip_file.read(name), path.read_bytes(), name)

        for required in (
            "Main/qt_app.py",
            "Main/qt_main_window.py",
            "Main/qt_math_keyboard.py",
            "Main/qt_result_workspace.py",
            "Main/math_editor/resources/editor.html",
            "Main/math_editor/resources/results.html",
        ):
            self.assertIn(required, actual)

        self.assertGreater(namespace["_APP_BUNDLE_SIZE"], 100 * 1024 * 1024)
        with tempfile.TemporaryDirectory() as temp_dir:
            app_archive = Path(temp_dir) / "embedded-app.tar.gz"
            namespace["_copy_embedded_app_archive"](app_archive)
            self.assertEqual(
                app_archive.stat().st_size,
                namespace["_APP_BUNDLE_SIZE"],
            )

            app_dir = Path(temp_dir) / "Test.app"
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
            invalid_version = versions / "Resources"
            invalid_version.mkdir(parents=True)
            namespace["_protect_embedded_webengine_layout"](app_dir)
            self.assertFalse(invalid_version.exists())
            self.assertEqual(versions.stat().st_mode & 0o777, 0o555)


if __name__ == "__main__":
    unittest.main()
