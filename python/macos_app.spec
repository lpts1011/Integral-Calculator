# -*- mode: python ; coding: utf-8 -*-

import os

app_name = "Integral_Calculator_Python"
app_version = os.environ.get("APP_VERSION", "6.0").strip()
if not app_version:
    raise ValueError("APP_VERSION must not be empty")
hiddenimports = [
    "locales.en",
    "locales.zh_cn",
    "locales.zh_tw",
    "locales.ja",
    "locales.ko",
    "locales.es",
    "locales.fr",
    "locales.ar",
    "locales.hi",
    "matplotlib.backends.backend_qtagg",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
]

a = Analysis(
    ["Integral_Calculator.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("calengine", "calengine"),
        ("numpy", "numpy"),
        ("solving", "solving"),
        ("math_editor/resources", "math_editor/resources"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={
        "matplotlib": {
            "backends": ["QtAgg"],
        },
    },
    runtime_hooks=[],
    excludes=[
        "_tkinter",
        "tkinter",
        "tests",
        "matplotlib.tests",
        "scipy._lib.tests",
        "scipy.cluster.tests",
        "scipy.constants.tests",
        "scipy.datasets",
        "scipy.fft.tests",
        "scipy.fftpack.tests",
        "scipy.integrate.tests",
        "scipy.interpolate.tests",
        "scipy.io.tests",
        "scipy.linalg.tests",
        "scipy.ndimage.tests",
        "scipy.optimize.tests",
        "scipy.signal.tests",
        "scipy.sparse.tests",
        "scipy.spatial.tests",
        "scipy.special.tests",
        "scipy.stats.tests",
        "solving.testing",
        "solving.testing.tests",
        "solving.integrals.tests",
        "solving.solvers.tests",
        "solving.utilities.tests",
        "IPython",
        "pytest",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name,
)

app = BUNDLE(
    coll,
    name=f"{app_name}.app",
    icon=None,
    bundle_identifier="com.peichili.integralcalculator",
    info_plist={
        "CFBundleName": "Integral Calculator",
        "CFBundleDisplayName": "Integral Calculator",
        "CFBundleShortVersionString": app_version,
        "CFBundleVersion": app_version,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "13.0",
    },
)
