import ast
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).parents[1]
EXPECTED_MATHLIVE_VERSION = "0.110.0"


class QtPackagingTests(unittest.TestCase):
    def test_entry_point_uses_qt_app(self):
        source = (PROJECT_ROOT / "Integral_Calculator.py").read_text(encoding="utf-8")
        self.assertIn("from qt_app import main as run_app", source)
        self.assertNotIn("from app_gui import main as run_app", source)

    def test_removed_toolbar_features_have_no_runtime_modules(self):
        self.assertFalse((PROJECT_ROOT / "favorites_store.py").exists())
        self.assertFalse((PROJECT_ROOT / "export_utils.py").exists())
        source = (PROJECT_ROOT / "qt_main_window.py").read_text(encoding="utf-8")
        self.assertNotIn("favorite", source.lower())
        self.assertNotIn("export", source.lower())

    def test_specs_bundle_live_editor_and_qt_webengine(self):
        for filename in ("macos_app.spec", "windows_app.spec"):
            with self.subTest(filename=filename):
                source = (PROJECT_ROOT / filename).read_text(encoding="utf-8")
                self.assertIn(
                    '("math_editor/resources", "math_editor/resources")',
                    source,
                )
                self.assertIn("PySide6.QtWebEngineCore", source)
                self.assertIn("PySide6.QtWebEngineWidgets", source)
                self.assertIn("PySide6.QtWebChannel", source)
                self.assertIn('"backends": ["QtAgg"]', source)
                self.assertNotIn("backend_tkagg", source)

    def test_macos_build_checks_live_editor_assets_before_building(self):
        source = (PROJECT_ROOT / "build_macos_app.sh").read_text(encoding="utf-8")
        self.assertIn("math_editor/resources/editor.html", source)
        self.assertIn("math_editor/resources/results.html", source)
        self.assertIn("math_editor/resources/mathlive.min.js", source)
        self.assertIn("math_editor/resources/fonts", source)
        self.assertIn('WEBENGINE_FRAMEWORK=', source)
        self.assertIn('Versions/Resources', source)
        self.assertIn('EXTRA_WEBENGINE_VERSION/Resources', source)
        self.assertIn('EXTRA_WEBENGINE_VERSION/Helpers', source)
        self.assertIn('codesign --verify --deep --strict "$SIGNING_APP"', source)
        self.assertIn('codesign --verify --deep --strict "$INSTALLED_APP"', source)
        self.assertIn('LOCAL_APP_LINK="Integral_Calculator_Python.app"', source)
        self.assertIn('Unsafe application install path', source)
        self.assertIn('PYTHON_BIN="${PYTHON_BIN:-python3}"', source)
        self.assertIn("import PySide6, PySide6.QtWebEngineWidgets", source)
        self.assertIn('"$PYTHON_BIN" -m PyInstaller', source)

    def test_specs_exclude_inactive_tk_runtime(self):
        for filename in ("macos_app.spec", "windows_app.spec"):
            with self.subTest(filename=filename):
                source = (PROJECT_ROOT / filename).read_text(encoding="utf-8")
                self.assertIn('"_tkinter"', source)
                self.assertIn('"tkinter"', source)

    def test_shared_qt_modules_do_not_import_tk_at_startup(self):
        for filename in ("plot_utils.py", "theme_utils.py"):
            with self.subTest(filename=filename):
                source = (PROJECT_ROOT / filename).read_text(encoding="utf-8")
                tree = ast.parse(source)
                top_level_imports = []
                for statement in tree.body:
                    if isinstance(statement, ast.Import):
                        top_level_imports.extend(alias.name for alias in statement.names)
                    elif isinstance(statement, ast.ImportFrom):
                        top_level_imports.append(statement.module or "")
                self.assertNotIn("tkinter", top_level_imports)
                self.assertNotIn("matplotlib.backends.backend_tkagg", top_level_imports)

    def test_mathlive_assets_are_complete_and_offline(self):
        root = PROJECT_ROOT / "math_editor" / "resources"
        self.assertTrue((root / "mathlive.min.js").is_file())
        self.assertGreater((root / "mathlive.min.js").stat().st_size, 0)
        self.assertTrue((root / "fonts").is_dir())
        font_files = sorted(root.joinpath("fonts").glob("*.woff2"))
        self.assertTrue(font_files)
        self.assertIn("KaTeX_Main-Regular.woff2", {font.name for font in font_files})
        self.assertIn("KaTeX_Size4-Regular.woff2", {font.name for font in font_files})
        version_file = root / "mathlive.version"
        self.assertTrue(version_file.is_file())
        version = version_file.read_text(encoding="utf-8").strip()
        self.assertEqual(EXPECTED_MATHLIVE_VERSION, version)
        checksum_file = root / "mathlive.min.js.sha256"
        self.assertTrue(checksum_file.is_file())
        if not checksum_file.is_file():
            return
        checksum_record = checksum_file.read_text(encoding="utf-8").split()
        self.assertEqual(["mathlive.min.js"], checksum_record[1:])
        actual_checksum = hashlib.sha256((root / "mathlive.min.js").read_bytes()).hexdigest()
        self.assertEqual(actual_checksum, checksum_record[0])
        html = (root / "editor.html").read_text(encoding="utf-8")
        self.assertIn("./mathlive.min.js", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("http://", html)
        results_html = (root / "results.html").read_text(encoding="utf-8")
        self.assertIn("./mathlive.min.js", results_html)
        self.assertNotIn("https://", results_html)
        self.assertNotIn("http://", results_html)

    def test_resource_root_uses_source_resources(self):
        module_path = PROJECT_ROOT / "math_editor" / "resource_paths.py"
        self.assertTrue(module_path.is_file())
        from math_editor.resource_paths import resource_root

        self.assertEqual(PROJECT_ROOT / "math_editor" / "resources", resource_root())

    def test_resource_root_uses_pyinstaller_meipass(self):
        module_path = PROJECT_ROOT / "math_editor" / "resource_paths.py"
        self.assertTrue(module_path.is_file())
        from math_editor.resource_paths import resource_root

        with tempfile.TemporaryDirectory() as temporary_directory:
            meipass = Path(temporary_directory)
            with patch.object(sys, "_MEIPASS", str(meipass), create=True):
                self.assertEqual(meipass / "math_editor" / "resources", resource_root())

    def test_runtime_resource_root_stages_and_refreshes_unsafe_source_path(self):
        import math_editor.resource_paths as resource_paths

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            source = temporary_root / "Peichi's Folder" / "resources"
            source.mkdir(parents=True)
            (source / "editor.html").write_text("first", encoding="utf-8")
            (source / "mathlive.version").write_text("0.110.0", encoding="utf-8")
            cache_root = temporary_root / "safe-cache"

            with patch.object(resource_paths, "resource_root", return_value=source):
                staged = resource_paths.runtime_resource_root(cache_root)
                self.assertNotIn("'", str(staged))
                self.assertEqual("first", (staged / "editor.html").read_text())

                (source / "editor.html").write_text("second", encoding="utf-8")
                refreshed = resource_paths.runtime_resource_root(cache_root)
                self.assertNotEqual(staged, refreshed)
                self.assertEqual("second", (refreshed / "editor.html").read_text())

    def test_runtime_resource_root_rejects_symlink_cache_root(self):
        import math_editor.resource_paths as resource_paths

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            source = temporary_root / "resources"
            source.mkdir()
            (source / "editor.html").write_text("trusted", encoding="utf-8")
            (source / "mathlive.version").write_text("0.110.0", encoding="utf-8")
            real_cache = temporary_root / "real-cache"
            real_cache.mkdir()
            linked_cache = temporary_root / "linked-cache"
            linked_cache.symlink_to(real_cache, target_is_directory=True)

            with patch.object(resource_paths, "resource_root", return_value=source):
                with self.assertRaises(RuntimeError):
                    resource_paths.runtime_resource_root(linked_cache)

    def test_runtime_resource_root_is_reused_safely_across_threads(self):
        import math_editor.resource_paths as resource_paths

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            source = temporary_root / "resources"
            source.mkdir()
            (source / "editor.html").write_text("trusted", encoding="utf-8")
            (source / "mathlive.version").write_text("0.110.0", encoding="utf-8")
            cache_root = temporary_root / "safe-cache"

            with patch.object(resource_paths, "resource_root", return_value=source):
                with ThreadPoolExecutor(max_workers=8) as executor:
                    staged = list(
                        executor.map(
                            lambda _: resource_paths.runtime_resource_root(cache_root),
                            range(24),
                        )
                    )

            self.assertEqual(1, len(set(staged)))
            self.assertEqual("trusted", (staged[0] / "editor.html").read_text())

    def test_runtime_resource_root_rejects_modified_staged_assets(self):
        import math_editor.resource_paths as resource_paths

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            source = temporary_root / "resources"
            source.mkdir()
            (source / "editor.html").write_text("trusted", encoding="utf-8")
            (source / "mathlive.version").write_text("0.110.0", encoding="utf-8")
            cache_root = temporary_root / "safe-cache"

            with patch.object(resource_paths, "resource_root", return_value=source):
                staged = resource_paths.runtime_resource_root(cache_root)
                staged_editor = staged / "editor.html"
                staged_editor.write_text("untrusted", encoding="utf-8")
                with self.assertRaises(RuntimeError):
                    resource_paths.runtime_resource_root(cache_root)
                staged_editor.write_text("trusted", encoding="utf-8")

    def test_vendor_script_rejects_wrong_mathlive_version(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            archive = temporary_root / "mathlive-wrong-version.tgz"
            with tarfile.open(archive, "w:gz") as package:
                files = {
                    "package/package.json": json.dumps({"version": "0.109.0"}).encode(),
                    "package/mathlive.min.js": b"wrong version",
                    "package/fonts/KaTeX_Main-Regular.woff2": b"font",
                    "package/LICENSE.txt": b"license",
                }
                for name, contents in files.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(contents)
                    package.addfile(info, fileobj=io.BytesIO(contents))

            checkout = temporary_root / "Main"
            script = checkout / "scripts" / "vendor_mathlive.sh"
            script.parent.mkdir(parents=True)
            shutil.copy2(PROJECT_ROOT / "scripts" / "vendor_mathlive.sh", script)
            os.chmod(script, 0o755)

            result = subprocess.run(
                [str(script)],
                env={**os.environ, "MATHLIVE_TARBALL": str(archive)},
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(EXPECTED_MATHLIVE_VERSION, result.stderr)

    def test_vendor_script_vendors_valid_offline_tarball_to_override(self):
        script_source = (PROJECT_ROOT / "scripts" / "vendor_mathlive.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("MATHLIVE_DEST", script_source)
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            archive = temporary_root / "mathlive-valid.tgz"
            bundle = b"valid MathLive 0.110.0 fixture bundle"
            font = b"valid font fixture"
            license_text = b"valid MIT license fixture"
            with tarfile.open(archive, "w:gz") as package:
                files = {
                    "package/package.json": json.dumps(
                        {"name": "mathlive", "version": EXPECTED_MATHLIVE_VERSION}
                    ).encode(),
                    "package/mathlive.min.js": bundle,
                    "package/fonts/KaTeX_Main-Regular.woff2": font,
                    "package/LICENSE.txt": license_text,
                }
                for name, contents in files.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(contents)
                    package.addfile(info, fileobj=io.BytesIO(contents))

            checkout = temporary_root / "Main"
            script = checkout / "scripts" / "vendor_mathlive.sh"
            script.parent.mkdir(parents=True)
            shutil.copy2(PROJECT_ROOT / "scripts" / "vendor_mathlive.sh", script)
            os.chmod(script, 0o755)
            destination = temporary_root / "isolated-resources"
            notice_destination = temporary_root / "isolated-notices"
            project_bundle_before = (PROJECT_ROOT / "math_editor/resources/mathlive.min.js").read_bytes()
            project_version_before = (PROJECT_ROOT / "math_editor/resources/mathlive.version").read_bytes()
            project_checksum_before = (PROJECT_ROOT / "math_editor/resources/mathlive.min.js.sha256").read_bytes()

            result = subprocess.run(
                [str(script)],
                env={
                    **os.environ,
                    "MATHLIVE_TARBALL": str(archive),
                    "MATHLIVE_DEST": str(destination),
                    "MATHLIVE_NOTICE_DEST": str(notice_destination),
                },
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(bundle, (destination / "mathlive.min.js").read_bytes())
            self.assertEqual(
                EXPECTED_MATHLIVE_VERSION,
                (destination / "mathlive.version").read_text(encoding="utf-8").strip(),
            )
            checksum_record = (destination / "mathlive.min.js.sha256").read_text(
                encoding="utf-8"
            ).split()
            self.assertEqual(hashlib.sha256(bundle).hexdigest(), checksum_record[0])
            self.assertEqual(["mathlive.min.js"], checksum_record[1:])
            self.assertTrue((destination / "fonts").is_dir())
            self.assertEqual(font, (destination / "fonts/KaTeX_Main-Regular.woff2").read_bytes())
            self.assertEqual(
                license_text,
                (notice_destination / "mathlive_mit_license.txt").read_bytes(),
            )
            self.assertEqual(project_bundle_before, (PROJECT_ROOT / "math_editor/resources/mathlive.min.js").read_bytes())
            self.assertEqual(project_version_before, (PROJECT_ROOT / "math_editor/resources/mathlive.version").read_bytes())
            self.assertEqual(project_checksum_before, (PROJECT_ROOT / "math_editor/resources/mathlive.min.js.sha256").read_bytes())
