# -*- mode: python ; coding: utf-8 -*-

app_name = "Integral Calculator"
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
    "matplotlib.backends.backend_tkagg",
]

excludes = [
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
]

a = Analysis(
    ["Integral_Calculator.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("calengine", "calengine"),
        ("numpy", "numpy"),
        ("solving", "solving"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={
        "matplotlib": {
            "backends": ["TkAgg"],
        },
    },
    runtime_hooks=[],
    excludes=excludes,
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
    icon=None,
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
