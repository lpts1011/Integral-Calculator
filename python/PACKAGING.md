# Packaging

The desktop application uses PySide6, Qt WebEngine, and a fully local MathLive
bundle. It does not download editor code or fonts while running.

## Offline Math Editor Assets

The repository already contains the pinned MathLive bundle. To restore or
refresh that exact bundle from its npm package, run:

```bash
./scripts/vendor_mathlive.sh
```

The vendor script verifies MathLive `0.110.0`, writes the JavaScript checksum,
copies the required fonts, and preserves the license under
`THIRD_PARTY_NOTICES`. Both desktop build scripts bundle
`math_editor/resources` into the application.

## macOS `.app`

Build the local macOS desktop app from this folder:

```bash
./build_macos_app.sh
```

The script verifies that the selected Python contains PySide6, Qt WebEngine,
and PyInstaller before it can replace an installed app. When the dependencies
are in a specific environment, select it explicitly:

```bash
PYTHON_BIN=/path/to/environment/bin/python3 ./build_macos_app.sh
```

The build output is:

```text
dist/Integral_Calculator_Python.app
```

On macOS, Desktop folders managed by a file provider can immediately attach
Finder metadata that prevents code signing. The build script therefore signs a
metadata-free staging copy, installs the verified app at:

```text
~/Applications/Integral_Calculator_Python.app
```

and creates this clickable launcher beside the Python entry point:

```text
Main/Integral_Calculator_Python.app
```

The local launcher is a symbolic link to the complete signed app in
`~/Applications`. Set `INTEGRAL_CALCULATOR_APP_PATH` before building to choose a
different stable installation path.

If PyInstaller is missing, install it first:

```bash
python3 -m pip install --user pyinstaller
```

The app is ad-hoc signed for local macOS use. For public distribution outside
your own Mac, use an Apple Developer ID certificate and notarization.

## Windows `.exe`

PyInstaller is not a cross-compiler, so build the Windows version on a Windows
computer.

From this folder on Windows, run:

```bat
build_windows_app.bat
```

The generated executable is:

```text
dist\Integral_Calculator_Python\Integral_Calculator_Python.exe
```

Keep the whole `dist\Integral_Calculator_Python` folder together when moving the
program to another Windows computer, because the `.exe` uses the DLLs and
Python packages beside it.

You can also build it from GitHub Actions after pushing this folder as a
repository. Run the `Build Windows EXE` workflow, then download the
`Integral-Calculator-Windows` artifact.

## Runtime Stack

The production entry point is the PySide6 application. Matplotlib uses QtAgg,
and every mathematical expression field is rendered by the bundled MathLive
editor through Qt WebEngine. The older Tkinter modules remain in the source tree
only as a parity reference and are not imported by the production entry point.
